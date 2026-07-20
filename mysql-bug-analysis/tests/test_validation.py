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
            result = validate_fix(Path("scenario.yaml"), affected, fixed, Path("mysql"), Path(td), iterations=2, timeout=1)
            self.assertTrue(result["validated"])
            self.assertEqual(result["affected"]["triggered"], 2)
            self.assertEqual(result["fixed"]["triggered"], 0)


if __name__ == '__main__':
    unittest.main()
