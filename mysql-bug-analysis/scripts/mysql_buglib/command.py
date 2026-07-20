from __future__ import annotations

import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping


def run_command(
    argv: Iterable[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: int | None = None,
    log_path: Path | None = None,
    check: bool = False,
    stdin_text: str | None = None,
) -> dict:
    args = [str(item) for item in argv]
    started = datetime.now(timezone.utc)
    merged_env = os.environ.copy()
    if env:
        merged_env.update({str(k): str(v) for k, v in env.items()})
    try:
        process = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            input=stdin_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        process = None
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        returncode = 124
    else:
        stdout, stderr, returncode = process.stdout, process.stderr, process.returncode

    result = {
        "argv": args,
        "command_line": shlex.join(args),
        "cwd": str(cwd) if cwd else None,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "started_at": started.isoformat(),
        "duration_seconds": (datetime.now(timezone.utc) - started).total_seconds(),
    }
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if check and (timed_out or returncode != 0):
        raise subprocess.CalledProcessError(returncode, args, stdout, stderr)
    return result
