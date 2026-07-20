import os
import tempfile
import unittest
from pathlib import Path

from mysql_buglib.config import DEFAULT_CONFIG, load_config, validate_config


class ConfigTests(unittest.TestCase):
    def test_task_overrides_yaml_and_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "config.yaml"
            cfg_path.write_text(
                "paths:\n  source_root: /yaml/source\n  report_root: /yaml/reports\n"
                "build:\n  parallel_jobs: 4\n",
                encoding="utf-8",
            )
            cfg = load_config(
                cfg_path,
                overrides={"paths": {"source_root": "/task/source"}},
            )
            self.assertEqual(cfg["paths"]["source_root"], "/task/source")
            self.assertEqual(cfg["paths"]["report_root"], "/yaml/reports")
            self.assertEqual(cfg["build"]["parallel_jobs"], 4)
            self.assertEqual(
                cfg["source"]["official_repository"],
                DEFAULT_CONFIG["source"]["official_repository"],
            )

    def test_rejects_dangerous_runtime_root(self):
        cfg = load_config(None, overrides={"paths": {"runtime_root": "/var/lib/mysql"}})
        with self.assertRaises(ValueError):
            validate_config(cfg)

    def test_rejects_relative_roots(self):
        cfg = load_config(None, overrides={"paths": {"workspace_root": "relative/path"}})
        with self.assertRaises(ValueError):
            validate_config(cfg)


if __name__ == "__main__":
    unittest.main()
