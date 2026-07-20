from __future__ import annotations

import json
from pathlib import Path

from .command import run_command


def source_diff(before: Path, after: Path, evidence_dir: Path, paths: list[str] | None = None, timeout: int = 600) -> dict:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    output = evidence_dir / "source.diff"
    if (before / ".git").is_dir() and (after / ".git").is_dir() and before.resolve() == after.resolve():
        raise ValueError("For a single Git tree, use explicit commits; this command expects two source directories")
    cmd = ["diff", "-ruN", "--exclude=.git", "--exclude=CMakeFiles", "--exclude=*.o"]
    if paths:
        # diff has no clean multi-relative-path mode; compare selected pairs and concatenate.
        chunks = []
        results = []
        for relative in paths:
            result = run_command(cmd + [str(before / relative), str(after / relative)], timeout=timeout)
            chunks.append(result["stdout"])
            results.append(result["returncode"])
        output.write_text("\n".join(chunks), encoding="utf-8")
        returncode = 1 if any(code == 1 for code in results) else max(results, default=0)
    else:
        result = run_command(cmd + [str(before), str(after)], timeout=timeout, log_path=evidence_dir / "source-diff-command.json")
        output.write_text(result["stdout"], encoding="utf-8")
        returncode = result["returncode"]
    summary = {"before": str(before), "after": str(after), "diff": str(output), "differences_found": returncode == 1, "returncode": returncode}
    (evidence_dir / "source-diff-result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
