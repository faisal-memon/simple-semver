from __future__ import annotations

import json
from typing import TYPE_CHECKING
import urllib.error
import urllib.request

if TYPE_CHECKING:
    from config import GitHubConfig

SEMVER_LABELS = {
    "semver:major": "major",
    "semver:minor": "minor",
    "semver:patch": "patch",
}


class ActionError(Exception):
    pass


def resolve_version_bump_from_pr_labels(github: GitHubConfig, ignored_labels: set[str]) -> str | None:
    pulls = get_associated_pull_requests(github.token, github.api_url, github.repository, github.sha)
    selected_pr = select_pull_request_for_branch(pulls, github.target_branch)
    if selected_pr is None:
        return None

    pr_number = get_pull_request_number(selected_pr)
    labels = get_pull_request_labels(selected_pr)
    return resolve_bump_from_labels(pr_number, labels, ignored_labels)


def get_associated_pull_requests(github_token: str, api_url: str, repository: str, sha: str) -> list[dict]:
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
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise ActionError(f"Failed to query pull requests for commit {sha}: HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise ActionError(f"Failed to query pull requests for commit {sha}: {exc.reason}.") from exc


def select_pull_request_for_branch(pulls: list[dict], target_branch: str) -> dict | None:
    return next((pull for pull in pulls if pull.get("base", {}).get("ref") == target_branch), None)


def get_pull_request_number(pull_request: dict) -> int:
    return pull_request.get("number")


def get_pull_request_labels(pull_request: dict) -> list[str]:
    return [label.get("name", "") for label in pull_request.get("labels", [])]


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


