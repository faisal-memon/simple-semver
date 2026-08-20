#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys

from config import Config, env
from errors import ActionError
from git_ops import Git
from pr_labels import resolve_bump_from_labels
from semver import SemverTags


def main() -> int:
    config = Config.from_env()
    git = Git()
    semver_tags = SemverTags(config.tag_prefix)

    try:
        config.validate()
        bump_type = compute_bump_type(config, git)
        tags = git.list_tags()
        previous_tag = semver_tags.get_latest_tag(tags)
        new_tag = semver_tags.bump_tag(previous_tag, bump_type)
        log_info(f"Resolved bump={bump_type} from previous={previous_tag} to new={new_tag}")

        if config.write_tag:
            log_info(f"write-tag=true; creating and pushing {new_tag}")
            git.push_tag(new_tag)

            if config.write_major_tag:
                major_tag = semver_tags.major_tag_for(new_tag)
                log_info(f"write-major-tag=true; updating floating major tag {major_tag}")
                git.push_major_tag(major_tag)

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


def compute_bump_type(config: Config, git: Git) -> str:
    if config.version_bump:
        return config.version_bump

    pulls = git.get_associated_pull_requests(config.github)
    selected_pr = select_pull_request_for_branch(pulls, config.github.target_branch)
    if selected_pr is None:
        return "patch"

    pr_number = selected_pr.get("number")
    labels = [label.get("name", "") for label in selected_pr.get("labels", [])]
    bump_type = resolve_bump_from_labels(pr_number, labels, config.ignored_labels)
    if bump_type:
        return bump_type

    return "patch"


def select_pull_request_for_branch(pulls: list[dict], target_branch: str) -> dict | None:
    return next((pull for pull in pulls if pull.get("base", {}).get("ref") == target_branch), None)


def write_outputs(new_tag: str, previous_tag: str, version_bump_used: str) -> None:
    output_path = env("GITHUB_OUTPUT")
    if not output_path:
        raise ActionError("GITHUB_OUTPUT is required to write action outputs.")

    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"new-tag={new_tag}\n")
        handle.write(f"previous-tag={previous_tag}\n")
        handle.write(f"version-bump-used={version_bump_used}\n")


def log_info(message: str) -> None:
    print(f"[pr-label-semver] {message}")


if __name__ == "__main__":
    raise SystemExit(main())
