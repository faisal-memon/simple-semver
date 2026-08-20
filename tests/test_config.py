import unittest

import github_labels
from config import Config, GitHubConfig


class ConfigValidationTests(unittest.TestCase):
    def test_requires_pr_label_inputs_when_version_bump_empty(self):
        config = Config(
            version_bump="",
            github=GitHubConfig(
                token="token",
                api_url="https://api.github.com",
                repository="",
                sha="",
                target_branch="",
            ),
            ignored_labels=set(),
            write_tag=False,
            write_major_tag=False,
            tag_prefix="v",
        )

        with self.assertRaisesRegex(github_labels.ActionError, "GITHUB_REPOSITORY is required"):
            config.validate()

    def test_skips_pr_label_requirements_when_version_bump_is_set(self):
        config = Config(
            version_bump="patch",
            github=GitHubConfig(
                token="",
                api_url="https://api.github.com",
                repository="",
                sha="",
                target_branch="",
            ),
            ignored_labels=set(),
            write_tag=False,
            write_major_tag=False,
            tag_prefix="v",
        )

        config.validate()


if __name__ == "__main__":
    unittest.main()
