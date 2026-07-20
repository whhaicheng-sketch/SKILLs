from __future__ import annotations

import json
import shutil
from pathlib import Path

from .command import run_command
from .discovery import inspect_source_tree, scan_source_trees
from .safety import create_owned_dir


def find_local_source(root: Path, version: str) -> Path | None:
    for item in scan_source_trees(root, managed=False):
        if item.get("version") == version and item.get("valid_source_tree"):
            return Path(item["path"])
    return None


def mysql_tag(version: str) -> str:
    return f"mysql-{version}"


def acquire_source(config: dict, version: str, evidence_dir: Path) -> dict:
    local = find_local_source(Path(config["paths"]["source_root"]), version)
    if local:
        result = inspect_source_tree(local, managed=False)
        result["source_origin"] = "local"
    else:
        managed_root = Path(config["paths"]["managed_source_root"])
        existing = find_local_source(managed_root, version)
        if existing:
            result = inspect_source_tree(existing, managed=True)
            result["source_origin"] = "managed-existing"
        else:
            if not config["source"].get("allow_download", True):
                raise FileNotFoundError(f"MySQL {version} source not found and downloads are disabled")
            target = managed_root / f"mysql-{version}"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise FileExistsError(f"Target exists but is not a valid source tree: {target}")
            cmd = [
                "git", "clone", "--branch", mysql_tag(version), "--single-branch",
                "--depth", str(config["source"].get("clone_depth", 1)),
                config["source"]["official_repository"], str(target),
            ]
            log = evidence_dir / f"acquire-source-{version}.json"
            run_command(cmd, timeout=3600, log_path=log, check=True)
            create_owned_dir(target, config["safety"]["ownership_marker"], adopt_existing=True)
            exclude = target / ".git" / "info" / "exclude"
            exclude.parent.mkdir(parents=True, exist_ok=True)
            marker = config["safety"]["ownership_marker"]
            current = exclude.read_text(encoding="utf-8", errors="replace") if exclude.exists() else ""
            if marker not in current.splitlines():
                exclude.write_text(current + ("" if current.endswith("\n") or not current else "\n") + marker + "\n", encoding="utf-8")
            result = inspect_source_tree(target, managed=True)
            result["source_origin"] = "official-git"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    manifest = evidence_dir / f"source-{version}.json"
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def create_instrumentation_copy(config: dict, source: Path, bug_id: str, version: str) -> Path:
    root = Path(config["paths"]["managed_source_root"])
    target = root / "instrumented" / f"BUG-{bug_id}" / f"mysql-{version}"
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    create_owned_dir(target, config["safety"]["ownership_marker"], adopt_existing=True)
    return target
