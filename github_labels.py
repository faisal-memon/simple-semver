from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SEMVER_LABELS = {
    "semver:major": "major",
    "semver:minor": "minor",
    "semver:patch": "patch",
}


class ActionError(Exception):
    pass


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
    target_branch = require_env(
        "GITHUB_REF_NAME",
        "GITHUB_REF_NAME is required to resolve version bump from PR labels.",
    )
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


def parse_ignored_labels(raw_value: str) -> set[str]:
    if raw_value == "":
        return set()
    return {normalize_label(part) for part in raw_value.split(",") if normalize_label(part)}


def normalize_label(label: str) -> str:
    return label.strip().lower()


def require_env(var_name: str, error_message: str) -> str:
    value = env(var_name)
    if not value:
        raise ActionError(error_message)
    return value


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
