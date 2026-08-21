from __future__ import annotations

from errors import ActionError

SEMVER_LABELS = {
    "semver:major": "major",
    "semver:minor": "minor",
    "semver:patch": "patch",
}


def resolve_bump_from_labels(pr_number: int, labels: list[str], ignored_labels: set[str]) -> str | None:
    """Resolve a single bump type from the labels present on a PR."""
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
    """Parse and normalize the configured comma-separated ignored labels."""
    if raw_value == "":
        return set()
    return {normalize_label(part) for part in raw_value.split(",") if normalize_label(part)}


def normalize_label(label: str) -> str:
    """Normalize a label for case-insensitive comparisons."""
    return label.strip().lower()
