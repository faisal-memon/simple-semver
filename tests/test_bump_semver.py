import unittest
import github_labels
from semver import SemverTags


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


class SemverTagsTests(unittest.TestCase):
    def test_bump_tag_patch(self):
        self.assertEqual(SemverTags("v").bump_tag("v1.2.3", "patch"), "v1.2.4")

    def test_bump_tag_minor(self):
        self.assertEqual(SemverTags("v").bump_tag("v1.2.3", "minor"), "v1.3.0")

    def test_bump_tag_major(self):
        self.assertEqual(SemverTags("v").bump_tag("v1.2.3", "major"), "v2.0.0")

    def test_rejects_invalid_bump(self):
        with self.assertRaisesRegex(github_labels.ActionError, "Unsupported version bump"):
            SemverTags("v").bump_tag("v1.2.3", "banana")

    def test_get_latest_tag_returns_zero_baseline_with_prefix(self):
        git = FakeGit([])

        self.assertEqual(SemverTags("v").get_latest_tag(git), "v0.0.0")
        self.assertTrue(git.fetch_tags_called)
        self.assertEqual(git.patterns, ["v[0-9]*.[0-9]*.[0-9]*"])

    def test_get_latest_tag_returns_first_sorted_matching_tag(self):
        git = FakeGit(["v2.3.4", "v2.3.3", "other"])

        self.assertEqual(SemverTags("v").get_latest_tag(git), "v2.3.4")

    def test_major_tag_for(self):
        self.assertEqual(SemverTags("v").major_tag_for("v2.3.4"), "v2")


class FakeGit:
    def __init__(self, tags):
        self.tags = tags
        self.fetch_tags_called = False
        self.patterns = []

    def fetch_tags(self):
        self.fetch_tags_called = True

    def list_tags(self, pattern):
        self.patterns.append(pattern)
        return self.tags


if __name__ == "__main__":
    unittest.main()
