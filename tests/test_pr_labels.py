import unittest

from config import GitHubConfig
from pr_labels import parse_ignored_labels, resolve_bump_from_labels


class ParseIgnoredLabelsTests(unittest.TestCase):
    def test_empty_value_disables_ignored_labels(self):
        self.assertEqual(parse_ignored_labels(""), set())

    def test_normalizes_labels(self):
        self.assertEqual(
            parse_ignored_labels(" Dependencies, Needs-Review "),
            {"dependencies", "needs-review"},
        )


class ResolveBumpFromLabelsTests(unittest.TestCase):
    def test_returns_none_when_only_ignored_labels_exist(self):
        result = resolve_bump_from_labels(
            10,
            ["dependencies", "team:platform"],
            {"dependencies"},
        )
        self.assertIsNone(result)

    def test_resolves_namespaced_label(self):
        result = resolve_bump_from_labels(
            11,
            ["dependencies", "semver:minor"],
            {"dependencies"},
        )
        self.assertEqual(result, "minor")

    def test_rejects_multiple_semver_labels(self):
        from errors import ActionError

        with self.assertRaisesRegex(ActionError, "Multiple version labels"):
            resolve_bump_from_labels(
                12,
                ["semver:patch", "semver:major"],
                set(),
            )


class PullRequestSelectionTests(unittest.TestCase):
    def test_selects_matching_target_branch(self):
        from main import select_pull_request_for_branch

        pulls = [
            {"number": 1, "base": {"ref": "release"}},
            {"number": 2, "base": {"ref": "main"}},
        ]

        selected_pr = select_pull_request_for_branch(pulls, "main")

        self.assertEqual(selected_pr["number"], 2)


class PullRequestResolutionFlowTests(unittest.TestCase):
    def test_compute_bump_type_uses_associated_pr_labels(self):
        from config import Config
        from main import compute_bump_type

        config = Config(
            version_bump="",
            github=GitHubConfig(
                token="token",
                api_url="https://api.github.com",
                repository="owner/repo",
                sha="abc123",
                target_branch="main",
            ),
            ignored_labels={"dependencies"},
            write_tag=False,
            write_major_tag=False,
            tag_prefix="v",
        )
        git = FakeGitForPulls([
            {
                "number": 42,
                "base": {"ref": "main"},
                "labels": [{"name": "semver:minor"}],
            }
        ])

        result = compute_bump_type(config, git)

        self.assertEqual(result, "minor")
        self.assertIs(git.github_arg, config.github)


class FakeGitForPulls:
    def __init__(self, pulls):
        self.pulls = pulls
        self.github_arg = None

    def get_associated_pull_requests(self, github):
        self.github_arg = github
        return self.pulls


if __name__ == "__main__":
    unittest.main()
