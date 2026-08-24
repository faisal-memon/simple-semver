import unittest

from config import Config, GitHubConfig
from errors import ActionError


class ConfigValidationTests(unittest.TestCase):
    def test_requires_pr_label_inputs_when_version_bump_override_empty(self):
        config = Config(
            version_bump_override="",
            github=GitHubConfig(
                token="token",
                api_url="https://api.github.com",
                repository="",
                sha="",
                target_branch="",
            ),
            write_tag=False,
            write_major_tag=False,
            tag_prefix="v",
        )

        with self.assertRaisesRegex(ActionError, "GITHUB_REPOSITORY is required"):
            config.validate()

    def test_skips_pr_label_requirements_when_version_bump_override_is_set(self):
        config = Config(
            version_bump_override="patch",
            github=GitHubConfig(
                token="",
                api_url="https://api.github.com",
                repository="",
                sha="",
                target_branch="",
            ),
            write_tag=False,
            write_major_tag=False,
            tag_prefix="v",
        )

        config.validate()


if __name__ == "__main__":
    unittest.main()
