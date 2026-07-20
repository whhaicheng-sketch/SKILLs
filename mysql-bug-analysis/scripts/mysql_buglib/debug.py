from __future__ import annotations

import json
from pathlib import Path

from .command import run_command


def default_gdb_commands(mode: str, output_log: Path, breakpoints: list[str] | None = None) -> str:
    commands = [
        "set pagination off",
        "set confirm off",
        "set print pretty on",
        f"set logging file {output_log}",
        "set logging overwrite on",
        "set logging enabled on",
        "handle SIGPIPE nostop noprint pass",
    ]
    for breakpoint in breakpoints or []:
        commands.append(f"break {breakpoint}")
    if mode == "launch":
        commands += ["run", "thread apply all bt full", "info registers"]
    elif mode == "attach":
        commands += ["info threads", "thread apply all bt full", "detach"]
    elif mode == "core":
        commands += ["info threads", "thread apply all bt full", "info registers", "frame 0", "info args", "info locals"]
    commands += ["set logging enabled off", "quit"]
    return "\n".join(commands) + "\n"


def run_gdb(
    *, gdb_path: Path, mode: str, mysqld: Path, evidence_dir: Path,
    defaults_file: Path | None = None, pid: int | None = None,
    core_file: Path | None = None, commands_file: Path | None = None,
    breakpoints: list[str] | None = None, timeout: int = 1800,
) -> dict:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    session_log = evidence_dir / "gdb-session.log"
    if commands_file is None:
        commands_file = evidence_dir / "gdb-commands.gdb"
        commands_file.write_text(default_gdb_commands(mode, session_log, breakpoints), encoding="utf-8")
    cmd = [str(gdb_path), "--batch", "-x", str(commands_file)]
    if mode == "launch":
        cmd += ["--args", str(mysqld)]
        if defaults_file:
            cmd.append(f"--defaults-file={defaults_file}")
    elif mode == "attach":
        if not pid:
            raise ValueError("attach mode requires pid")
        cmd += [str(mysqld), "-p", str(pid)]
    elif mode == "core":
        if not core_file:
            raise ValueError("core mode requires core_file")
        cmd += [str(mysqld), str(core_file)]
    else:
        raise ValueError(f"Unsupported GDB mode: {mode}")
    result = run_command(cmd, timeout=timeout, log_path=evidence_dir / "gdb-command.json")
    summary = {
        "success": result["returncode"] == 0,
        "mode": mode,
        "mysqld": str(mysqld),
        "commands_file": str(commands_file),
        "session_log": str(session_log),
        "returncode": result["returncode"],
    }
    (evidence_dir / "gdb-result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
