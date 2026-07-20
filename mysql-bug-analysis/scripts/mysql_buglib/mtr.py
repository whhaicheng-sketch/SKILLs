from __future__ import annotations

import json
from pathlib import Path

from .command import run_command


def locate_mtr(source_dir: Path, build_dir: Path | None = None) -> Path:
    candidates = [
        source_dir / "mysql-test" / "mysql-test-run.pl",
        (build_dir / "mysql-test" / "mysql-test-run.pl") if build_dir else Path("/__missing__"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("mysql-test-run.pl not found")


def run_mtr(source_dir: Path, test_names: list[str], evidence_dir: Path, build_dir: Path | None = None, extra_args: list[str] | None = None, timeout: int = 3600) -> dict:
    mtr = locate_mtr(source_dir, build_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["perl", str(mtr), "--force", "--retry=0", "--max-test-fail=1"]
    if build_dir:
        cmd.append(f"--vardir={evidence_dir / 'var'}")
    cmd += list(extra_args or []) + test_names
    result = run_command(cmd, cwd=mtr.parent, timeout=timeout, log_path=evidence_dir / "mtr-command.json")
    summary = {
        "success": result["returncode"] == 0,
        "tests": test_names,
        "returncode": result["returncode"],
        "command_log": str(evidence_dir / "mtr-command.json"),
    }
    (evidence_dir / "mtr-result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
