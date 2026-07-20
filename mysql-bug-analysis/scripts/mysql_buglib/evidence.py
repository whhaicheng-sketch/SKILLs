from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_file(source: Path, destination_dir: Path, category: str, description: str = "") -> dict:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / source.name
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return {
        "category": category,
        "description": description,
        "path": str(target),
        "size": target.stat().st_size,
        "sha256": sha256(target),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def build_evidence_index(workspace: Path) -> list[dict]:
    evidence_root = workspace / "evidence"
    items = []
    if not evidence_root.exists():
        return items
    for path in sorted(p for p in evidence_root.rglob("*") if p.is_file()):
        items.append({
            "id": f"E{len(items) + 1:03d}",
            "category": path.relative_to(evidence_root).parts[0],
            "path": str(path.relative_to(workspace)),
            "size": path.stat().st_size,
            "sha256": sha256(path),
        })
    (workspace / "evidence-index.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return items
