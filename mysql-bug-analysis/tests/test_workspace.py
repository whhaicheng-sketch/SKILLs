import tempfile
import unittest
from pathlib import Path

from mysql_buglib.workspace import create_workspace


class WorkspaceTests(unittest.TestCase):
    def test_workspace_has_expected_structure_and_marker(self):
        with tempfile.TemporaryDirectory() as td:
            ws = create_workspace(Path(td), "109595", ".mysql-bug-skill-owned")
            self.assertTrue((ws / ".mysql-bug-skill-owned").exists())
            self.assertTrue((ws / "evidence" / "official").is_dir())
            self.assertTrue((ws / "reproduction").is_dir())
            self.assertTrue((ws / "reports").is_dir())
            self.assertTrue((ws / "state.json").exists())


if __name__ == "__main__":
    unittest.main()

class WorkspaceNamingTests(unittest.TestCase):
    def test_local_prefix_is_not_duplicated(self):
        from mysql_buglib.workspace import workspace_path
        self.assertEqual(workspace_path(Path('/tmp'), 'LOCAL-20260720-001').name, 'LOCAL-20260720-001')
