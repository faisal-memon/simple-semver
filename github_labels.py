from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import GitHubConfig
    from git_ops import Git

SEMVER_LABELS = {
    "semver:major": "major",
    "semver:minor": "minor",
    "semver:patch": "patch",
}


class ActionError(Exception):
    pass


def resolve_version_bump_from_pr_labels(git: Git, github: GitHubConfig, ignored_labels: set[str]) -> str | None:
    pulls = git.get_associated_pull_requests(github)
    selected_pr = select_pull_request_for_branch(pulls, github.target_branch)
    if selected_pr is None:
        return None

    pr_number = selected_pr.get("number")
    labels = [label.get("name", "") for label in selected_pr.get("labels", [])]
    return resolve_bump_from_labels(pr_number, labels, ignored_labels)


def select_pull_request_for_branch(pulls: list[dict], target_branch: str) -> dict | None:
    return next((pull for pull in pulls if pull.get("base", {}).get("ref") == target_branch), None)


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
