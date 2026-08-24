import unittest

from config import GitHubConfig
from pr_labels import resolve_bump_from_labels


class ResolveBumpFromLabelsTests(unittest.TestCase):
    def test_returns_none_when_no_semver_labels_exist(self):
        result = resolve_bump_from_labels(
            10,
            ["dependencies", "team:platform"],
        )
        self.assertIsNone(result)

    def test_resolves_namespaced_label(self):
        result = resolve_bump_from_labels(
            11,
            ["dependencies", "semver:minor"],
        )
        self.assertEqual(result, "minor")

    def test_rejects_multiple_semver_labels(self):
        from errors import ActionError

        with self.assertRaisesRegex(ActionError, "Multiple version labels"):
            resolve_bump_from_labels(
                12,
                ["semver:patch", "semver:major"],
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
            write_tag=False,
            write_major_tag=False,
            tag_prefix="v",
        )
        git = FakeGitForPullRequestLabels(None)

        result = compute_bump_type(config, git)

        self.assertEqual(result, "patch")
        self.assertIs(git.github_arg, config.github)

    def test_compute_bump_type_defaults_for_dependency_pull_request(self):
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
            write_tag=False,
            write_major_tag=False,
            tag_prefix="v",
        )
        git = FakeGitForPullRequestLabels((42, ["dependencies", "team:platform"]))

        self.assertEqual(compute_bump_type(config, git), "patch")


class FakeGitForPullRequestLabels:
    def __init__(self, pull_request_labels):
        self.pull_request_labels = pull_request_labels
        self.github_arg = None

    def get_pull_request_labels(self, github):
        self.github_arg = github
        return self.pull_request_labels


if __name__ == "__main__":
    unittest.main()
