import unittest

import bump_semver
import github_labels


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


class BumpFromPreviousTests(unittest.TestCase):
    def test_patch_bump(self):
        self.assertEqual(bump_semver.bump_from_previous("1.2.3", "patch"), "1.2.4")

    def test_minor_bump(self):
        self.assertEqual(bump_semver.bump_from_previous("1.2.3", "minor"), "1.3.0")

    def test_major_bump(self):
        self.assertEqual(bump_semver.bump_from_previous("1.2.3", "major"), "2.0.0")

    def test_rejects_invalid_bump(self):
        with self.assertRaisesRegex(github_labels.ActionError, "Unsupported version bump"):
            bump_semver.bump_from_previous("1.2.3", "banana")


if __name__ == "__main__":
    unittest.main()
