from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .evidence import build_evidence_index


def _load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _join(values: Any) -> str:
    if not values:
        return "待确认"
    if isinstance(values, str):
        return values
    return ", ".join(str(x) for x in values)


def _evidence_table(items: list[dict]) -> str:
    lines = ["| 编号 | 类型 | 路径 | SHA-256 |", "|---|---|---|---|"]
    for item in items:
        lines.append(f"| {item['id']} | {item['category']} | `{item['path']}` | `{item['sha256']}` |")
    return "\n".join(lines) if items else "尚未收集证据。"


def _replace(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def report_artifact_id(bug_id: str) -> str:
    upper = bug_id.upper()
    return bug_id if upper.startswith("BUG-") else f"BUG-{bug_id}"


def render_reports(workspace: Path, report_root: Path, assets_dir: Path, *, force: bool = False) -> dict[str, str]:
    metadata = _load_json(workspace / "metadata.json", {})
    state = _load_json(workspace / "state.json", {})
    bug_id = str(metadata.get("bug_id") or state.get("bug_id") or workspace.name)
    evidence = build_evidence_index(workspace)
    artifact_id = report_artifact_id(bug_id)
    output_dir = report_root / artifact_id
    output_dir.mkdir(parents=True, exist_ok=True)
    values = {
        "BUG_ID": bug_id,
        "TITLE": str(metadata.get("title") or "待确认"),
        "COMPONENT": str(metadata.get("component") or "待确认"),
        "ANALYSIS_DATE": str(metadata.get("analysis_date") or date.today().isoformat()),
        "AFFECTED_VERSIONS": _join(metadata.get("affected_versions")),
        "FIXED_VERSIONS": _join(metadata.get("fixed_versions")),
        "REPRODUCTION_STATUS": str(metadata.get("reproduction_status") or ("reproduced" if state.get("reproduced") else "not-reproduced")),
        "FIX_VALIDATION_STATUS": str(metadata.get("fix_validation_status") or ("validated" if state.get("fix_validated") else "not-validated")),
        "CONFIDENCE_LEVEL": str(metadata.get("confidence_level") or state.get("confidence_level") or "L5"),
        "EVIDENCE_TABLE": _evidence_table(evidence),
        "WORKSPACE": str(workspace),
    }
    analysis = _replace((assets_dir / "bug-analysis-template.md").read_text(encoding="utf-8"), values)
    reproduction = _replace((assets_dir / "bug-reproduction-template.md").read_text(encoding="utf-8"), values)
    analysis_path = output_dir / f"{artifact_id}-analysis.md"
    reproduction_path = output_dir / f"{artifact_id}-reproduction.md"
    if not force and (analysis_path.exists() or reproduction_path.exists()):
        raise FileExistsError(f"Reports already exist under {output_dir}; use force only when overwrite is intentional")
    analysis_path.write_text(analysis, encoding="utf-8")
    reproduction_path.write_text(reproduction, encoding="utf-8")
    return {"analysis": str(analysis_path), "reproduction": str(reproduction_path)}
