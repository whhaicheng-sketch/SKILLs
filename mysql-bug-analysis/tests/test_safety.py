import tempfile
import unittest
from pathlib import Path

from mysql_buglib.safety import create_owned_dir, safe_remove_tree


class SafetyTests(unittest.TestCase):
    def test_cleanup_requires_marker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            victim = root / "victim"
            victim.mkdir()
            with self.assertRaises(PermissionError):
                safe_remove_tree(victim, root, ".mysql-bug-skill-owned")

    def test_owned_directory_can_be_removed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            victim = create_owned_dir(root / "victim", ".mysql-bug-skill-owned")
            (victim / "data.txt").write_text("x", encoding="utf-8")
            safe_remove_tree(victim, root, ".mysql-bug-skill-owned")
            self.assertFalse(victim.exists())


if __name__ == "__main__":
    unittest.main()

class OwnershipAdoptionTests(unittest.TestCase):
    def test_nonempty_unowned_directory_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "existing"
            target.mkdir()
            (target / "foreign.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(PermissionError):
                create_owned_dir(target, ".mysql-bug-skill-owned")
