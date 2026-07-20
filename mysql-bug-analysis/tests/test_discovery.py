import tempfile
import unittest
from pathlib import Path

from mysql_buglib.discovery import parse_mysql_version, scan_source_trees


class DiscoveryTests(unittest.TestCase):
    def test_parse_mysql_version(self):
        text = """
        SET(MYSQL_VERSION_MAJOR 8)
        SET(MYSQL_VERSION_MINOR 0)
        SET(MYSQL_VERSION_PATCH 36)
        SET(MYSQL_VERSION_EXTRA \"\")
        """
        self.assertEqual(parse_mysql_version(text), "8.0.36")

    def test_scan_source_trees_reads_source_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "mysql-8.0.36"
            (src / "sql").mkdir(parents=True)
            (src / "storage" / "innobase").mkdir(parents=True)
            (src / "CMakeLists.txt").write_text("project(mysql)", encoding="utf-8")
            (src / "MYSQL_VERSION").write_text(
                "SET(MYSQL_VERSION_MAJOR 8)\n"
                "SET(MYSQL_VERSION_MINOR 0)\n"
                "SET(MYSQL_VERSION_PATCH 36)\n",
                encoding="utf-8",
            )
            items = scan_source_trees(Path(td), managed=False)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["version"], "8.0.36")
            self.assertTrue(items[0]["valid_source_tree"])
            self.assertFalse(items[0]["managed"])


if __name__ == "__main__":
    unittest.main()

class EnvironmentDiscoveryTests(unittest.TestCase):
    def test_environment_includes_resources_and_debug_settings(self):
        from mysql_buglib.config import load_config
        from mysql_buglib.discovery import discover_environment
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in ["source", "managed", "build", "install", "runtime", "workspace", "reports", "cache"]:
                (root / name).mkdir()
            cfg = load_config(None, overrides={"paths": {
                "source_root": str(root / "source"),
                "managed_source_root": str(root / "managed"),
                "build_root": str(root / "build"),
                "install_root": str(root / "install"),
                "runtime_root": str(root / "runtime"),
                "workspace_root": str(root / "workspace"),
                "report_root": str(root / "reports"),
                "cache_root": str(root / "cache"),
            }})
            result = discover_environment(cfg, root / "out")
            self.assertIn("resources", result)
            self.assertIn("debug", result)
            self.assertIn("running_mysql", result)
            self.assertIn("disk", result["resources"])
