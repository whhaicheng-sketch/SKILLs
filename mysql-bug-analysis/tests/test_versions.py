import unittest

from mysql_buglib.versions import resolve_version_roles


class VersionTests(unittest.TestCase):
    def test_explicit_versions_override_research_candidates(self):
        result = resolve_version_roles(
            research={"versions_mentioned": ["8.0.30", "8.0.32"], "fixed_version_candidates": ["8.0.32"]},
            local_versions=["8.0.30", "8.0.36"],
            affected="8.0.31",
            fixed="8.0.33",
        )
        self.assertEqual(result["recommended_affected_version"], "8.0.31")
        self.assertEqual(result["recommended_fixed_version"], "8.0.33")

    def test_does_not_treat_a_mentioned_version_as_affected(self):
        result = resolve_version_roles(
            research={"versions_mentioned": ["8.0.30", "8.0.32"], "fixed_version_candidates": ["8.0.32"]},
            local_versions=[],
        )
        self.assertIsNone(result["recommended_affected_version"])
        self.assertEqual(result["recommended_fixed_version"], "8.0.32")

    def test_does_not_guess_affected_version_from_local_inventory_only(self):
        result = resolve_version_roles(
            research={},
            local_versions=["8.0.36", "8.4.0"],
        )
        self.assertIsNone(result["recommended_affected_version"])
        self.assertIsNone(result["recommended_fixed_version"])


if __name__ == '__main__':
    unittest.main()
