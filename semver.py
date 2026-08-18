from __future__ import annotations

import re
from typing import Callable

from github_labels import ActionError

SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class SemverTags:
    def __init__(self, tag_prefix: str) -> None:
        self.tag_prefix = tag_prefix

    def get_latest_tag(self, git_runner: Callable[..., object]) -> str:
        git_runner("fetch", "--tags", "--force", check=False, capture_output=True)
        result = git_runner(
            "tag",
            "-l",
            f"{self.tag_prefix}[0-9]*.[0-9]*.[0-9]*",
            "--sort=-version:refname",
            capture_output=True,
        )
        tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        matching_tags = [tag for tag in tags if self._matches_prefixed_semver(tag)]
        if not matching_tags:
            return f"{self.tag_prefix}0.0.0"
        latest_tag = matching_tags[0]
        self.validate_tag(latest_tag)
        return latest_tag

    def bump_tag(self, latest_tag: str, bump_type: str) -> str:
        version = self._strip_prefix(latest_tag)
        self.validate_tag(latest_tag)
        return f"{self.tag_prefix}{self._bump_version(version, bump_type)}"

    def validate_tag(self, tag: str) -> None:
        if not self._matches_prefixed_semver(tag):
            raise ActionError(
                f"Latest tag must be semantic version format {self.tag_prefix}X.Y.Z, "
                f"but got {tag}. Fix tags or set an explicit version-bump."
            )

    def major_tag_for(self, tag: str) -> str:
        version = self._strip_prefix(tag)
        self.validate_tag(tag)
        major = version.split(".", 1)[0]
        return f"{self.tag_prefix}{major}"

    def _strip_prefix(self, tag: str) -> str:
        if not tag.startswith(self.tag_prefix):
            raise ActionError(
                f"Expected tag prefix {self.tag_prefix} in {tag}. Fix tags or set an explicit version-bump."
            )
        return tag[len(self.tag_prefix) :]

    def _matches_prefixed_semver(self, tag: str) -> bool:
        if not tag.startswith(self.tag_prefix):
            return False
        return bool(SEMVER_RE.match(tag[len(self.tag_prefix) :]))

    def _bump_version(self, previous_version: str, bump_type: str) -> str:
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
