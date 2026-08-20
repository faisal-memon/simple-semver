import unittest

import github_labels
from config import GitHubConfig


class ParseIgnoredLabelsTests(unittest.TestCase):
    def test_empty_value_disables_ignored_labels(self):
        self.assertEqual(github_labels.parse_ignored_labels(""), set())

    def test_normalizes_labels(self):
        self.assertEqual(
            github_labels.parse_ignored_labels(" Dependencies, Needs-Review "),
            {"dependencies", "needs-review"},
        )


class ResolveBumpFromLabelsTests(unittest.TestCase):
    def test_returns_none_when_only_ignored_labels_exist(self):
        result = github_labels.resolve_bump_from_labels(
            10,
            ["dependencies", "team:platform"],
            {"dependencies"},
        )
        self.assertIsNone(result)

    def test_resolves_namespaced_label(self):
        result = github_labels.resolve_bump_from_labels(
            11,
            ["dependencies", "semver:minor"],
            {"dependencies"},
        )
        self.assertEqual(result, "minor")

    def test_rejects_multiple_semver_labels(self):
        with self.assertRaisesRegex(github_labels.ActionError, "Multiple version labels"):
            github_labels.resolve_bump_from_labels(
                12,
                ["semver:patch", "semver:major"],
                set(),
            )


class ResolveVersionBumpFromPrLabelsTests(unittest.TestCase):
    def test_uses_git_for_associated_pull_requests(self):
        git = FakeGitForPulls([
            {
                "number": 42,
                "base": {"ref": "main"},
                "labels": [{"name": "semver:minor"}],
            }
        ])
        github = GitHubConfig(
            token="token",
            api_url="https://api.github.com",
            repository="owner/repo",
            sha="abc123",
            target_branch="main",
        )

        result = github_labels.resolve_version_bump_from_pr_labels(git, github, {"dependencies"})

        self.assertEqual(result, "minor")
        self.assertIs(git.github_arg, github)


class FakeGitForPulls:
    def __init__(self, pulls):
        self.pulls = pulls
        self.github_arg = None

    def get_associated_pull_requests(self, github):
        self.github_arg = github
        return self.pulls


if __name__ == "__main__":
    unittest.main()
