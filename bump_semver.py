#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys

from config import Config, env
from github_labels import ActionError, resolve_version_bump_from_pr_labels
from semver import SemverTags


def main() -> int:
    config = Config.from_env()
    semver_tags = SemverTags(config.tag_prefix)

    try:
        config.validate()
        bump_type = compute_bump_type(config)
        previous_tag = semver_tags.get_latest_tag(git)
        new_tag = semver_tags.bump_tag(previous_tag, bump_type)
        log_info(f"Resolved bump={bump_type} from previous={previous_tag} to new={new_tag}")

        if config.write_tag:
            log_info(f"write-tag=true; creating and pushing {new_tag}")
            push_tag(new_tag)

            if config.write_major_tag:
                major_tag = semver_tags.major_tag_for(new_tag)
                log_info(f"write-major-tag=true; updating floating major tag {major_tag}")
                push_major_tag(major_tag)

        write_outputs(new_tag, previous_tag, bump_type)
        log_info(
            "Wrote outputs "
            f"new-tag={new_tag} previous-tag={previous_tag} version-bump-used={bump_type}"
        )
        return 0
    except ActionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        output = f"{exc.stdout or ''}{exc.stderr or ''}".strip()
        if output:
            print(output, file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return exc.returncode or 1


def compute_bump_type(config: Config) -> str:
    if config.version_bump:
        return config.version_bump

    bump_type = resolve_version_bump_from_pr_labels(config.github_token, config.api_url, config.ignored_labels)
    if bump_type:
        return bump_type

    return "patch"


def push_tag(tag_name: str) -> None:
    ensure_local_tag_absent(tag_name)
    git("tag", tag_name)
    result = git("push", "origin", f"refs/tags/{tag_name}", check=False, capture_output=True)
    if result.returncode == 0:
        return

    ensure_local_tag_absent(tag_name)
    output = f"{result.stdout}{result.stderr}".strip()
    if "already exists" in output:
        raise ActionError(
            f"Tag collision for {tag_name}. Enable workflow concurrency (cancel-in-progress: false) and rerun.\n{output}"
        )

    raise ActionError(output or f"Failed to push tag {tag_name}.")


def push_major_tag(tag_name: str) -> None:
    git("tag", "-f", tag_name, check=False, capture_output=True)
    result = git("push", "-f", "origin", f"refs/tags/{tag_name}", check=False, capture_output=True)
    if result.returncode != 0:
        output = f"{result.stdout}{result.stderr}".strip()
        raise ActionError(output or f"Failed to push tag {tag_name}.")


def write_outputs(new_tag: str, previous_tag: str, version_bump_used: str) -> None:
    output_path = env("GITHUB_OUTPUT")
    if not output_path:
        raise ActionError("GITHUB_OUTPUT is required to write action outputs.")

    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"new-tag={new_tag}\n")
        handle.write(f"previous-tag={previous_tag}\n")
        handle.write(f"version-bump-used={version_bump_used}\n")


def ensure_local_tag_absent(tag_name: str) -> None:
    existing = git("rev-parse", "-q", "--verify", f"refs/tags/{tag_name}", check=False)
    if existing.returncode == 0:
        git("tag", "-d", tag_name, check=False, capture_output=True)


def git(*args: str, capture_output: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=check,
        text=True,
        capture_output=capture_output,
    )


def log_info(message: str) -> None:
    print(f"[pr-label-semver] {message}")


if __name__ == "__main__":
    raise SystemExit(main())
