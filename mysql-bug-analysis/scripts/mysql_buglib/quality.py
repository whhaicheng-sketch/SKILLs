from __future__ import annotations

import json
import re
from pathlib import Path

_REQUIRED_ANALYSIS = ["执行摘要", "版本影响范围", "源码执行路径", "根本原因", "修复补丁分析", "可信度评级", "证据索引"]
_REQUIRED_REPRO = ["实验环境", "编译 Debug", "建立正常基线", "最小复现场景", "GDB", "修复版本验证", "环境清理", "证据索引"]
_PLACEHOLDERS = [r"\{\{[^}]+\}\}", r"\bTBD\b", r"\bTODO\b", r"待补充"]


def check_report(path: Path, required: list[str]) -> list[str]:
    if not path.is_file():
        return [f"Missing report: {path}"]
    text = path.read_text(encoding="utf-8")
    errors = [f"Missing section containing: {item}" for item in required if item not in text]
    for pattern in _PLACEHOLDERS:
        if re.search(pattern, text, flags=re.I):
            errors.append(f"Unresolved placeholder pattern: {pattern}")
    return errors


def report_check(report_dir: Path, bug_id: str) -> dict:
    analysis = report_dir / f"BUG-{bug_id}-analysis.md"
    reproduction = report_dir / f"BUG-{bug_id}-reproduction.md"
    errors = check_report(analysis, _REQUIRED_ANALYSIS) + check_report(reproduction, _REQUIRED_REPRO)
    return {"success": not errors, "errors": errors, "analysis": str(analysis), "reproduction": str(reproduction)}
