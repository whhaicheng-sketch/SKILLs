import unittest

from mysql_buglib.confidence import evaluate_confidence


class ConfidenceTests(unittest.TestCase):
    def test_l1_requires_reproduction_fix_and_dynamic_source_alignment(self):
        result = evaluate_confidence({
            "reproduced": True,
            "fix_validated": True,
            "dynamic_evidence": True,
            "source_evidence": True,
            "official_evidence": True,
        })
        self.assertEqual(result["level"], "L1")

    def test_static_only_is_l4(self):
        result = evaluate_confidence({"source_evidence": True})
        self.assertEqual(result["level"], "L4")

    def test_natural_reproduction_without_forced_trigger_is_not_l2(self):
        result = evaluate_confidence({"reproduced": True, "source_evidence": True, "patch_evidence": True})
        self.assertEqual(result["level"], "L4")

    def test_l3_requires_official_fix_test_not_merely_any_official_file(self):
        result = evaluate_confidence({"official_evidence": True, "source_evidence": True, "patch_evidence": True})
        self.assertEqual(result["level"], "L4")


if __name__ == "__main__":
    unittest.main()
