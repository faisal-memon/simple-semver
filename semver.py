from __future__ import annotations

import re

from github_labels import ActionError

SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def resolve_latest_semver_tag(tag_prefix: str, tags: list[str]) -> str:
    matching_tags = [tag for tag in tags if _matches_prefixed_semver(tag_prefix, tag)]
    if not matching_tags:
        return "0.0.0"
    return matching_tags[0][len(tag_prefix) :]


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


def _matches_prefixed_semver(tag_prefix: str, tag: str) -> bool:
    if not tag.startswith(tag_prefix):
        return False
    return bool(SEMVER_RE.match(tag[len(tag_prefix) :]))
