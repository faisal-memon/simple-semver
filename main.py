#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys

from config import Config, env
from errors import ActionError
from git_ops import Git
from pr_labels import has_ignored_label, resolve_bump_from_labels
from semver import SemverTags


def main() -> int:
    """Run the action entrypoint and report a process-style exit code."""
    config = Config.from_env()
    git = Git()
    semver_tags = SemverTags(config.tag_prefix)

    try:
        config.validate()
        # First determine the type of bump: major, minor, or patch
        # The bump is determined first by override in the action and then
        # labels on the PR.
        bump_type = compute_bump_type(config, git)
        if bump_type is None:
            write_outputs("", "", "", release_skipped=True)
            log_info("Skipping release because the associated PR has an ignored label and no semver label")
            return 0

        # Bump the latest tag with the configured prefix.
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

        write_outputs(new_tag, previous_tag, bump_type, release_skipped=False)
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


def compute_bump_type(config: Config, git: Git) -> str | None:
    """Resolve the bump type from an explicit override or PR labels."""
    if config.version_bump_override:
        return config.version_bump_override

    pull_request_labels = git.get_pull_request_labels(config.github)
    if pull_request_labels is None:
        return "patch"

    pr_number, labels = pull_request_labels
    bump_type = resolve_bump_from_labels(pr_number, labels, config.ignored_labels)
    if bump_type:
        return bump_type

    if has_ignored_label(labels, config.ignored_labels):
        log_info(
            f"PR #{pr_number} has an ignored label and no semver label; skipping the release. "
            "Add exactly one semver:major, semver:minor, or semver:patch label to release it."
        )
        return None

    return "patch"


def write_outputs(new_tag: str, previous_tag: str, version_bump_used: str, *, release_skipped: bool) -> None:
    """Append action outputs to the GitHub output file."""
    output_path = env("GITHUB_OUTPUT")
    if not output_path:
        raise ActionError("GITHUB_OUTPUT is required to write action outputs.")

    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"new-tag={new_tag}\n")
        handle.write(f"previous-tag={previous_tag}\n")
        handle.write(f"version-bump-used={version_bump_used}\n")
        handle.write(f"release-skipped={'true' if release_skipped else 'false'}\n")


def log_info(message: str) -> None:
    """Print a consistently prefixed informational log line."""
    print(f"[pr-label-semver] {message}")


if __name__ == "__main__":
    raise SystemExit(main())
