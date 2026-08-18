#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys

from github_labels import ActionError, parse_ignored_labels, resolve_version_bump_from_pr_labels
from semver import SemverTags


def main() -> int:
    version_bump = env("INPUT_VERSION_BUMP")
    github_token = env("INPUT_GITHUB_TOKEN") or env("GITHUB_TOKEN")
    ignored_labels = parse_ignored_labels(env("INPUT_IGNORE_LABELS", "dependencies"))
    write_tag = env_bool("INPUT_WRITE_TAG", default=False)
    write_major_tag = env_bool("INPUT_WRITE_MAJOR_TAG", default=False)
    semver_tags = SemverTags(env("INPUT_TAG_PREFIX", "v"))

    try:
        resolved_bump = compute_version_bump(version_bump, github_token, ignored_labels)
        previous_tag = get_latest_semver_tag(semver_tags)
        new_tag = semver_tags.bump_tag(previous_tag, resolved_bump)
        log_info(f"Resolved bump={resolved_bump} from previous={previous_tag} to new={new_tag}")

        if write_tag:
            log_info(f"write-tag=true; creating and pushing {new_tag}")
            push_tag(new_tag)

            if write_major_tag:
                major_tag = semver_tags.major_tag_for(new_tag)
                log_info(f"write-major-tag=true; updating floating major tag {major_tag}")
                push_major_tag(major_tag)

        write_outputs(new_tag, previous_tag, resolved_bump)
        log_info(
            "Wrote outputs "
            f"new-tag={new_tag} previous-tag={previous_tag} version-bump-used={resolved_bump}"
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


def compute_version_bump(explicit_bump: str, github_token: str, ignored_labels: set[str]) -> str:
    if explicit_bump:
        return explicit_bump

    resolved_bump = resolve_version_bump_from_pr_labels(github_token, ignored_labels)
    if resolved_bump:
        return resolved_bump

    return "patch"


def get_latest_semver_tag(semver_tags: SemverTags) -> str:
    fetch_tags()
    tags = list_semver_tags(semver_tags.tag_prefix)
    latest_tag = semver_tags.resolve_latest_tag(tags)
    semver_tags.validate_tag(latest_tag)
    return latest_tag


def fetch_tags() -> None:
    git("fetch", "--tags", "--force", check=False, capture_output=True)


def list_semver_tags(tag_prefix: str) -> list[str]:
    result = git(
        "tag",
        "-l",
        f"{tag_prefix}[0-9]*.[0-9]*.[0-9]*",
        "--sort=-version:refname",
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


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


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name, "true" if default else "false").strip().lower()
    return value == "true"


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def log_info(message: str) -> None:
    print(f"[pr-label-semver] {message}")


if __name__ == "__main__":
    raise SystemExit(main())
