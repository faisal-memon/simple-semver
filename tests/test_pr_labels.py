import unittest

from config import GitHubConfig
from pr_labels import has_ignored_label, parse_ignored_labels, resolve_bump_from_labels


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

    def test_detects_ignored_label(self):
        self.assertTrue(has_ignored_label(["Dependencies", "team:platform"], {"dependencies"}))

    def test_does_not_detect_ignored_label_when_none_match(self):
        self.assertFalse(has_ignored_label(["team:platform"], {"dependencies"}))

    def test_rejects_multiple_semver_labels(self):
        from errors import ActionError

        with self.assertRaisesRegex(ActionError, "Multiple version labels"):
            resolve_bump_from_labels(
                12,
                ["semver:patch", "semver:major"],
                set(),
            )


class PullRequestResolutionFlowTests(unittest.TestCase):
    def test_compute_bump_type_uses_pull_request_labels_from_git(self):
        from config import Config
        from main import compute_bump_type

        config = Config(
            version_bump_override="",
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
        git = FakeGitForPullRequestLabels((42, ["semver:minor"]))

        result = compute_bump_type(config, git)

        self.assertEqual(result, "minor")
        self.assertIs(git.github_arg, config.github)

    def test_compute_bump_type_defaults_when_no_matching_pull_request_exists(self):
        from config import Config
        from main import compute_bump_type

        config = Config(
            version_bump_override="",
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
        git = FakeGitForPullRequestLabels(None)

        result = compute_bump_type(config, git)

        self.assertEqual(result, "patch")
        self.assertIs(git.github_arg, config.github)

    def test_compute_bump_type_stops_for_ignored_only_pull_request(self):
        from config import Config
        from errors import ActionError
        from main import compute_bump_type

        config = Config(
            version_bump_override="",
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
        git = FakeGitForPullRequestLabels((42, ["dependencies", "team:platform"]))

        with self.assertRaisesRegex(ActionError, "no release tag will be created"):
            compute_bump_type(config, git)


class FakeGitForPullRequestLabels:
    def __init__(self, pull_request_labels):
        self.pull_request_labels = pull_request_labels
        self.github_arg = None

    def get_pull_request_labels(self, github):
        self.github_arg = github
        return self.pull_request_labels


if __name__ == "__main__":
    unittest.main()
