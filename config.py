from __future__ import annotations

import os
from dataclasses import dataclass

from errors import ActionError


@dataclass
class GitHubConfig:
    """GitHub context required to inspect PR labels for a commit."""

    token: str
    api_url: str
    repository: str
    sha: str
    target_branch: str


@dataclass
class Config:
    """Top-level action configuration loaded from the environment."""

    version_bump_override: str
    github: GitHubConfig
    write_tag: bool
    write_major_tag: bool
    tag_prefix: str

    @classmethod
    def from_env(cls) -> Config:
        """Build config from action inputs and GitHub runtime variables."""
        return cls(
            version_bump_override=env("INPUT_VERSION_BUMP"),
            github=GitHubConfig(
                token=env_first("INPUT_GITHUB_TOKEN", "GITHUB_TOKEN"),
                api_url=env("GITHUB_API_URL", "https://api.github.com"),
                repository=env("GITHUB_REPOSITORY"),
                sha=env("GITHUB_SHA"),
                target_branch=env("GITHUB_REF_NAME"),
            ),
            write_tag=env_bool("INPUT_WRITE_TAG", default=False),
            write_major_tag=env_bool("INPUT_WRITE_MAJOR_TAG", default=False),
            tag_prefix=env("INPUT_TAG_PREFIX", "v"),
        )

    def validate(self) -> None:
        """Validate required runtime inputs for PR-label-driven bump resolution."""
        if self.version_bump_override:
            return

        if not self.github.token:
            raise ActionError("github-token (or GITHUB_TOKEN) is required when version-bump is empty.")
        if not self.github.repository:
            raise ActionError("GITHUB_REPOSITORY is required when version-bump is empty.")
        if not self.github.sha:
            raise ActionError("GITHUB_SHA is required when version-bump is empty.")
        if not self.github.target_branch:
            raise ActionError("GITHUB_REF_NAME is required when version-bump is empty.")


def env_first(*names: str) -> str:
    """Return the first non-empty environment value from the given names."""
    for name in names:
        value = env(name)
        if value:
            return value
    return ""


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean action input using true/false string semantics."""
    value = env(name, "true" if default else "false").strip().lower()
    return value == "true"


def env(name: str, default: str = "") -> str:
    """Read an environment variable with an optional default."""
    return os.environ.get(name, default)
