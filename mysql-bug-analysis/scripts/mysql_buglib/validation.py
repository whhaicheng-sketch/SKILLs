from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .reproduce import run_scenario


def validate_fix(
    scenario: Path,
    affected_manifest: dict,
    fixed_manifest: dict,
    affected_client: Path,
    fixed_client: Path,
    evidence_dir: Path,
    *,
    iterations: int,
    timeout: int,
    path_coverage_artifact: Path | None,
) -> dict:
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    if path_coverage_artifact is not None and not path_coverage_artifact.is_file():
        raise FileNotFoundError(path_coverage_artifact)
    path_coverage_confirmed = path_coverage_artifact is not None
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "affected": {"version": affected_manifest.get("version"), "iterations": iterations, "triggered": 0},
        "fixed": {"version": fixed_manifest.get("version"), "iterations": iterations, "triggered": 0},
    }
    for role, manifest, client in (("affected", affected_manifest, affected_client), ("fixed", fixed_manifest, fixed_client)):
        for index in range(1, iterations + 1):
            result = run_scenario(
                scenario,
                manifest,
                client,
                evidence_dir / role / f"iteration-{index:03d}",
                timeout,
            )
            if result.get("success"):
                summary[role]["triggered"] += 1
    summary["path_coverage_confirmed"] = path_coverage_confirmed
    summary["path_coverage_artifact"] = str(path_coverage_artifact) if path_coverage_artifact else None
    summary["path_coverage_sha256"] = hashlib.sha256(path_coverage_artifact.read_bytes()).hexdigest() if path_coverage_artifact else None
    summary["validated"] = summary["affected"]["triggered"] > 0 and summary["fixed"]["triggered"] == 0 and path_coverage_confirmed
    summary["limitation"] = None if path_coverage_confirmed else "Fixed-version trigger-path coverage was not confirmed; zero triggers is insufficient."
    (evidence_dir / "fix-validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
