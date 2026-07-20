import json
import tempfile
import unittest
from pathlib import Path

from mysql_buglib.reports import render_reports


class ReportTests(unittest.TestCase):
    def test_generates_two_markdown_reports(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            report_root = Path(td) / "reports"
            workspace.mkdir()
            (workspace / "metadata.json").write_text(json.dumps({
                "bug_id": "109595",
                "title": "Example crash",
                "component": "InnoDB",
                "affected_versions": ["8.0.30"],
                "fixed_versions": ["8.0.32"],
                "confidence_level": "L1",
                "reproduction_status": "reproduced",
                "fix_validation_status": "validated",
            }), encoding="utf-8")
            outputs = render_reports(workspace, report_root, Path(__file__).parents[1] / "assets")
            self.assertEqual(len(outputs), 2)
            analysis = Path(outputs["analysis"])
            reproduction = Path(outputs["reproduction"])
            self.assertTrue(analysis.exists())
            self.assertTrue(reproduction.exists())
            self.assertIn("根本原因", analysis.read_text(encoding="utf-8"))
            self.assertIn("GDB", reproduction.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

class ReportOverwriteTests(unittest.TestCase):
    def test_existing_reports_are_not_overwritten_without_force(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            report_root = Path(td) / "reports"
            workspace.mkdir()
            (workspace / "metadata.json").write_text(json.dumps({"bug_id": "1"}), encoding="utf-8")
            assets = Path(__file__).parents[1] / "assets"
            render_reports(workspace, report_root, assets)
            with self.assertRaises(FileExistsError):
                render_reports(workspace, report_root, assets)
