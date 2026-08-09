#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

SEMVER_LABELS = {
    "semver:major": "major",
    "semver:minor": "minor",
    "semver:patch": "patch",
}
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class ActionError(Exception):
    pass


def log_info(message: str) -> None:
    print(f"[pr-label-semver] {message}")


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name, "true" if default else "false").strip().lower()
    return value == "true"


def normalize_label(label: str) -> str:
    return label.strip().lower()


def parse_ignored_labels(raw_value: str) -> set[str]:
    if raw_value == "":
        return set()
    return {normalize_label(part) for part in raw_value.split(",") if normalize_label(part)}


def resolve_bump_from_labels(pr_number: int, labels: list[str], ignored_labels: set[str]) -> str | None:
    matched_bumps: list[str] = []
    for label in labels:
        normalized = normalize_label(label)
        if not normalized or normalized in ignored_labels:
            continue

        bump = SEMVER_LABELS.get(normalized)
        if bump is None:
            continue

        if bump not in matched_bumps:
            matched_bumps.append(bump)

    if len(matched_bumps) > 1:
        raise ActionError(
            f"Multiple version labels found on PR #{pr_number}. "
            "Use only one of semver:major, semver:minor, or semver:patch."
        )

    if matched_bumps:
        return matched_bumps[0]

    return None


def require_env(var_name: str, error_message: str) -> str:
    value = env(var_name)
    if not value:
        raise ActionError(error_message)
    return value


def resolve_version_bump_from_pr_labels(github_token: str, ignored_labels: set[str]) -> str | None:
    if not github_token:
        raise ActionError("github-token (or GITHUB_TOKEN) is required when version-bump is empty.")

    repository = require_env(
        "GITHUB_REPOSITORY",
        "GITHUB_REPOSITORY and GITHUB_SHA are required to resolve version bump from PR labels.",
    )
    sha = require_env(
        "GITHUB_SHA",
        "GITHUB_REPOSITORY and GITHUB_SHA are required to resolve version bump from PR labels.",
    )
    target_branch = require_env("GITHUB_REF_NAME", "GITHUB_REF_NAME is required to resolve version bump from PR labels.")
    api_url = env("GITHUB_API_URL", "https://api.github.com")
    owner, repo = repository.split("/", 1)

    request = urllib.request.Request(
        url=f"{api_url}/repos/{owner}/{repo}/commits/{sha}/pulls",
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            pulls = json.load(response)
    except urllib.error.HTTPError as exc:
        raise ActionError(f"Failed to query pull requests for commit {sha}: HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise ActionError(f"Failed to query pull requests for commit {sha}: {exc.reason}.") from exc

    selected_pr = next((pull for pull in pulls if pull.get("base", {}).get("ref") == target_branch), None)
    if selected_pr is None:
        return None

    pr_number = selected_pr.get("number")
    labels = [label.get("name", "") for label in selected_pr.get("labels", [])]
    return resolve_bump_from_labels(pr_number, labels, ignored_labels)


def compute_version_bump(explicit_bump: str, github_token: str, ignored_labels: set[str]) -> str:
    if explicit_bump:
        return explicit_bump

    resolved_bump = resolve_version_bump_from_pr_labels(github_token, ignored_labels)
    if resolved_bump:
        return resolved_bump

    return "patch"


def git(*args: str, capture_output: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=check,
        text=True,
        capture_output=capture_output,
    )


def resolve_latest_semver_tag(tag_prefix: str) -> str:
    result = git(
        "tag",
        "-l",
        f"{tag_prefix}[0-9]*.[0-9]*.[0-9]*",
        "--sort=-version:refname",
        capture_output=True,
    )
    tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not tags:
        return "0.0.0"

    return tags[0][len(tag_prefix):]


def validate_latest_tag_format(latest: str, tag_prefix: str) -> None:
    if not SEMVER_RE.match(latest):
        raise ActionError(
            f"Latest tag must be semantic version format {tag_prefix}X.Y.Z, "
            f"but got {tag_prefix}{latest}. Fix tags or set an explicit version-bump."
        )


def bump_from_previous(previous_version: str, bump_type: str) -> str:
    if not SEMVER_RE.match(previous_version):
        raise ActionError(f"Previous version must be semantic version format X.Y.Z, but got {previous_version}.")

    major_str, minor_str, patch_str = previous_version.split(".")
    major = int(major_str)
    minor = int(minor_str)
    patch = int(patch_str)

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ActionError(f"Unsupported version bump: {bump_type}")

    return f"{major}.{minor}.{patch}"


def ensure_local_tag_absent(tag_name: str) -> None:
    existing = git("rev-parse", "-q", "--verify", f"refs/tags/{tag_name}", check=False)
    if existing.returncode == 0:
        git("tag", "-d", tag_name, check=False, capture_output=True)


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
    output_path = require_env("GITHUB_OUTPUT", "GITHUB_OUTPUT is required to write action outputs.")
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"new-tag={new_tag}\n")
        handle.write(f"previous-tag={previous_tag}\n")
        handle.write(f"version-bump-used={version_bump_used}\n")


def main() -> int:
    version_bump = env("INPUT_VERSION_BUMP")
    tag_prefix = env("INPUT_TAG_PREFIX", "v")
    github_token = env("INPUT_GITHUB_TOKEN") or env("GITHUB_TOKEN")
    ignored_labels = parse_ignored_labels(env("INPUT_IGNORE_LABELS", "dependencies"))
    write_tag = env_bool("INPUT_WRITE_TAG", default=False)
    write_major_tag = env_bool("INPUT_WRITE_MAJOR_TAG", default=False)

    try:
        resolved_bump = compute_version_bump(version_bump, github_token, ignored_labels)
        git("fetch", "--tags", "--force", check=False, capture_output=True)
        latest_tag = resolve_latest_semver_tag(tag_prefix)
        validate_latest_tag_format(latest_tag, tag_prefix)
        previous_tag = f"{tag_prefix}{latest_tag}"
        next_version = bump_from_previous(latest_tag, resolved_bump)
        new_tag = f"{tag_prefix}{next_version}"
        log_info(f"Resolved bump={resolved_bump} from previous={previous_tag} to new={new_tag}")

        if write_tag:
            log_info(f"write-tag=true; creating and pushing {new_tag}")
            push_tag(new_tag)

            if write_major_tag:
                major_tag = f"{tag_prefix}{next_version.split('.', 1)[0]}"
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


if __name__ == "__main__":
    raise SystemExit(main())
