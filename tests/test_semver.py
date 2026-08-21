import unittest

from errors import ActionError
from semver import SemverTags


class SemverTagsTests(unittest.TestCase):
    def test_bump_tag_patch(self):
        self.assertEqual(SemverTags("v").bump_tag("v1.2.3", "patch"), "v1.2.4")

    def test_bump_tag_minor(self):
        self.assertEqual(SemverTags("v").bump_tag("v1.2.3", "minor"), "v1.3.0")

    def test_bump_tag_major(self):
        self.assertEqual(SemverTags("v").bump_tag("v1.2.3", "major"), "v2.0.0")

    def test_rejects_invalid_bump(self):
        with self.assertRaisesRegex(ActionError, "Unsupported version bump"):
            SemverTags("v").bump_tag("v1.2.3", "banana")

    def test_get_latest_tag_returns_zero_baseline_with_prefix(self):
        self.assertEqual(SemverTags("v").get_latest_tag([]), "v0.0.0")

    def test_get_latest_tag_returns_first_sorted_matching_tag(self):
        self.assertEqual(SemverTags("v").get_latest_tag(["v2.3.4", "v2.3.3", "other"]), "v2.3.4")

    def test_major_tag_for(self):
        self.assertEqual(SemverTags("v").major_tag_for("v2.3.4"), "v2")


if __name__ == "__main__":
    unittest.main()
