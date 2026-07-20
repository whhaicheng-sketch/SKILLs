from __future__ import annotations

import json
import re
from pathlib import Path

_REQUIRED_ANALYSIS = ["执行摘要", "版本影响范围", "源码执行路径", "根本原因", "修复补丁分析", "可信度评级", "证据索引"]
_REQUIRED_REPRO = ["实验环境", "编译 Debug", "建立正常基线", "最小复现场景", "GDB", "修复版本验证", "环境清理", "证据索引"]
_PLACEHOLDERS = [r"\{\{[^}]+\}\}", r"\bTBD\b", r"\bTODO\b", r"待补充"]
_LABEL = re.compile(r"\[(?:实验验证|官方确认|源码确认|补丁推导|合理推断|待验证)\]")
_CONFIDENCE = re.compile(r"\bL[1-5]\b")


def check_report(path: Path, required: list[str]) -> list[str]:
    if not path.is_file():
        return [f"Missing report: {path}"]
    text = path.read_text(encoding="utf-8")
    errors = [f"Missing section containing: {item}" for item in required if item not in text]
    for pattern in _PLACEHOLDERS:
        if re.search(pattern, text, flags=re.I):
            errors.append(f"Unresolved placeholder pattern: {pattern}")
    for target in re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)", text):
        if "://" in target or target.startswith("#"):
            continue
        clean = target.split("#", 1)[0]
        if clean and not (path.parent / clean).resolve().exists():
            errors.append(f"Broken local link: {target}")
    return errors


def report_check(report_dir: Path, bug_id: str) -> dict:
    analysis = report_dir / f"BUG-{bug_id}-analysis.md"
    reproduction = report_dir / f"BUG-{bug_id}-reproduction.md"
    errors = check_report(analysis, _REQUIRED_ANALYSIS) + check_report(reproduction, _REQUIRED_REPRO)
    texts = [p.read_text(encoding="utf-8") for p in (analysis, reproduction) if p.is_file()]
    combined = "\n".join(texts)
    if not _LABEL.search(combined):
        errors.append("Missing evidence label")
    if not _CONFIDENCE.search(combined):
        errors.append("Missing L1-L5 confidence level")
    if not any(term in combined for term in ("限制", "limitations", "局限")):
        errors.append("Missing limitations section")
    return {"success": not errors, "errors": errors, "analysis": str(analysis), "reproduction": str(reproduction)}
