import json
import tempfile
import unittest
from pathlib import Path

from mysql_buglib.reports import render_reports
from mysql_buglib.quality import report_check


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


class ReportQualityTests(unittest.TestCase):
    def test_rejects_reports_without_claim_labels_and_limitations(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            analysis = root / "BUG-1-analysis.md"
            reproduction = root / "BUG-1-reproduction.md"
            analysis.write_text("执行摘要 版本影响范围 源码执行路径 根本原因 修复补丁分析 可信度评级 L4 证据索引", encoding="utf-8")
            reproduction.write_text("实验环境 编译 Debug 建立正常基线 最小复现场景 GDB 修复版本验证 环境清理 证据索引", encoding="utf-8")
            result = report_check(root, "1")
            self.assertFalse(result["success"])
            self.assertTrue(any("evidence label" in error for error in result["errors"]))

    def test_rejects_broken_local_markdown_link(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            common = "[源码确认] 限制 L4 [missing](missing.log)"
            (root / "BUG-1-analysis.md").write_text("执行摘要 版本影响范围 源码执行路径 根本原因 修复补丁分析 可信度评级 证据索引 " + common, encoding="utf-8")
            (root / "BUG-1-reproduction.md").write_text("实验环境 编译 Debug 建立正常基线 最小复现场景 GDB 修复版本验证 环境清理 证据索引 " + common, encoding="utf-8")
            result = report_check(root, "1")
            self.assertTrue(any("Broken local link" in error for error in result["errors"]))
