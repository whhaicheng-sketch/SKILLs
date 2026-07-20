from __future__ import annotations

import json
from pathlib import Path

from .reproduce import run_scenario


def validate_fix(
    scenario: Path,
    affected_manifest: dict,
    fixed_manifest: dict,
    mysql_client: Path,
    evidence_dir: Path,
    *,
    iterations: int,
    timeout: int,
) -> dict:
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "affected": {"version": affected_manifest.get("version"), "iterations": iterations, "triggered": 0},
        "fixed": {"version": fixed_manifest.get("version"), "iterations": iterations, "triggered": 0},
    }
    for role, manifest in (("affected", affected_manifest), ("fixed", fixed_manifest)):
        for index in range(1, iterations + 1):
            result = run_scenario(
                scenario,
                manifest,
                mysql_client,
                evidence_dir / role / f"iteration-{index:03d}",
                timeout,
            )
            if result.get("success"):
                summary[role]["triggered"] += 1
    summary["validated"] = summary["affected"]["triggered"] > 0 and summary["fixed"]["triggered"] == 0
    summary["limitation"] = "Path coverage must be confirmed separately; zero triggers on fixed is not sufficient by itself."
    (evidence_dir / "fix-validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
