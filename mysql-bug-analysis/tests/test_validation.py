import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mysql_buglib.validation import validate_fix


class ValidationTests(unittest.TestCase):
    def test_fix_is_validated_when_affected_triggers_and_fixed_does_not(self):
        affected = {"version": "8.0.30", "role": "affected", "socket": "/a", "error_log": "/a.log"}
        fixed = {"version": "8.0.32", "role": "fixed", "socket": "/b", "error_log": "/b.log"}
        with tempfile.TemporaryDirectory() as td, patch(
            "mysql_buglib.validation.run_scenario",
            side_effect=[{"success": True}, {"success": True}, {"success": False}, {"success": False}],
        ):
            coverage = Path(td) / "coverage.json"; coverage.write_text("{}")
            result = validate_fix(Path("scenario.yaml"), affected, fixed, Path("mysql-a"), Path("mysql-b"), Path(td), iterations=2, timeout=1, path_coverage_artifact=coverage)
            self.assertTrue(result["validated"])
            self.assertEqual(result["affected"]["triggered"], 2)
            self.assertEqual(result["fixed"]["triggered"], 0)

    def test_fix_requires_path_coverage(self):
        affected = {"version": "8.0.30"}
        fixed = {"version": "8.0.32"}
        with tempfile.TemporaryDirectory() as td, patch(
            "mysql_buglib.validation.run_scenario",
            side_effect=[{"success": True}, {"success": False}],
        ):
            result = validate_fix(Path("scenario.yaml"), affected, fixed, Path("a"), Path("b"), Path(td), iterations=1, timeout=1, path_coverage_artifact=None)
            self.assertFalse(result["validated"])

    def test_each_role_uses_its_own_client(self):
        affected = {"version": "8.0.30"}
        fixed = {"version": "8.0.32"}
        with tempfile.TemporaryDirectory() as td, patch(
            "mysql_buglib.validation.run_scenario",
            side_effect=[{"success": True}, {"success": False}],
        ) as run:
            coverage = Path(td) / "coverage.json"; coverage.write_text("{}")
            validate_fix(Path("scenario.yaml"), affected, fixed, Path("a"), Path("b"), Path(td), iterations=1, timeout=1, path_coverage_artifact=coverage)
            self.assertEqual(run.call_args_list[0].args[2], Path("a"))
            self.assertEqual(run.call_args_list[1].args[2], Path("b"))

    def test_nonexistent_path_coverage_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                validate_fix(Path("scenario.yaml"), {}, {}, Path("a"), Path("b"), Path(td), iterations=1, timeout=1, path_coverage_artifact=Path(td) / "missing")


if __name__ == '__main__':
    unittest.main()
