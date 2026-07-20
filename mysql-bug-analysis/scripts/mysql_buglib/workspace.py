from __future__ import annotations

import json
import re
from pathlib import Path

from .safety import create_owned_dir
from .state import TaskState

_SUBDIRS = [
    "evidence/official", "evidence/source", "evidence/build", "evidence/runtime",
    "evidence/mtr", "evidence/gdb", "evidence/core", "evidence/logs",
    "evidence/sql", "evidence/patch", "reproduction", "reports",
]


def normalize_bug_id(value: str) -> str:
    value = str(value).strip()
    if re.fullmatch(r"\d+", value):
        return value
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    if not cleaned:
        raise ValueError("Invalid bug id")
    return cleaned


def workspace_path(root: Path, bug_id: str) -> Path:
    normalized = normalize_bug_id(bug_id)
    upper = normalized.upper()
    if upper.startswith("BUG-") or upper.startswith("LOCAL-"):
        return root / normalized
    prefix = "BUG" if normalized.isdigit() else "LOCAL"
    return root / f"{prefix}-{normalized}"


def create_workspace(root: Path, bug_id: str, marker: str) -> Path:
    path = workspace_path(root, bug_id)
    create_owned_dir(path, marker)
    for subdir in _SUBDIRS:
        (path / subdir).mkdir(parents=True, exist_ok=True)
    if not (path / "state.json").exists():
        TaskState.create(normalize_bug_id(bug_id), path / "state.json")
    task = path / "task.yaml"
    if not task.exists():
        task.write_text(f"bug_id: \"{normalize_bug_id(bug_id)}\"\n", encoding="utf-8")
    metadata = path / "metadata.json"
    if not metadata.exists():
        metadata.write_text(json.dumps({"bug_id": normalize_bug_id(bug_id)}, indent=2), encoding="utf-8")
    return path
