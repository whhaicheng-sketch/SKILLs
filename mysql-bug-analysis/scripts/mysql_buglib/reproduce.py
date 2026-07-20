from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

from .command import run_command

_ALLOWED_STEPS = {"sql", "sql_file", "sleep", "signal", "wait_for"}
_ALLOWED_CRITERIA = {"error_log_contains", "client_completed"}


def validate_scenario(scenario: dict[str, Any]) -> None:
    if not isinstance(scenario, dict):
        raise ValueError("Scenario must be a mapping")
    sessions = scenario.get("sessions", {})
    if not isinstance(sessions, dict):
        raise ValueError("sessions must be a mapping")
    criteria = scenario.get("success_criteria")
    if not isinstance(criteria, dict) or not criteria:
        raise ValueError("success_criteria must be a non-empty mapping")
    unknown = set(criteria) - _ALLOWED_CRITERIA
    if unknown:
        raise ValueError(f"Unsupported success criteria: {sorted(unknown)}")
    if "error_log_contains" in criteria and not isinstance(criteria["error_log_contains"], list):
        raise ValueError("error_log_contains must be a list")
    if "error_log_contains" in criteria and not criteria["error_log_contains"]:
        raise ValueError("error_log_contains must not be empty")
    if "client_completed" in criteria and not isinstance(criteria["client_completed"], bool):
        raise ValueError("client_completed must be boolean")
    for name, session in sessions.items():
        steps = session.get("steps", []) if isinstance(session, dict) else None
        if not isinstance(steps, list):
            raise ValueError(f"Session {name} steps must be a list")
        for step in steps:
            if not isinstance(step, dict) or len(step) != 1:
                raise ValueError(f"Each step must contain exactly one action: {step}")
            action = next(iter(step))
            if action not in _ALLOWED_STEPS:
                raise ValueError(f"Unknown scenario step: {action}")


def load_scenario(path: Path) -> dict[str, Any]:
    scenario = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    validate_scenario(scenario)
    return scenario


def _mysql(mysql_client: Path, socket_path: str, sql: str, log_path: Path, timeout: int) -> dict:
    return run_command(
        [str(mysql_client), f"--socket={socket_path}", "-uroot", "--batch", "--raw", "--skip-column-names", "-e", sql],
        timeout=timeout,
        log_path=log_path,
    )


class MysqlSession:
    """A persistent mysql CLI connection used by one logical scenario session."""

    def __init__(self, mysql_client: Path, socket_path: str, log_dir: Path, name: str):
        self.log_dir = log_dir
        self.name = name
        self.process = subprocess.Popen(
            [
                str(mysql_client), f"--socket={socket_path}", "-uroot",
                "--batch", "--raw", "--skip-column-names", "--unbuffered",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("Failed to open mysql session pipes")
        self.output: queue.Queue[str | None] = queue.Queue()
        self.reader = threading.Thread(target=self._read_output, name=f"mysql-reader-{name}", daemon=True)
        self.reader.start()

    def _read_output(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.output.put(line)
        self.output.put(None)

    def execute(self, sql: str, step_index: int, timeout: int) -> dict[str, Any]:
        marker = f"__MYSQL_BUG_SKILL_{uuid.uuid4().hex}__"
        statement = sql.rstrip().rstrip(";") + ";\n" if sql.strip() else ""
        statement += f"SELECT '{marker}';\n"
        started = time.monotonic()
        self.process.stdin.write(statement)
        self.process.stdin.flush()
        lines: list[str] = []
        deadline = time.monotonic() + timeout
        found = False
        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                line = self.output.get(timeout=remaining)
            except queue.Empty:
                break
            if line is None:
                break
            if marker in line:
                found = True
                break
            lines.append(line)
        timed_out = not found and self.process.poll() is None
        result = {
            "action": "sql",
            "returncode": 0 if found else (self.process.returncode if self.process.returncode is not None else 124),
            "stdout": "".join(lines),
            "timed_out": timed_out,
            "duration_seconds": time.monotonic() - started,
            "persistent_session": self.name,
        }
        path = self.log_dir / f"{self.name}-{step_index}.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        if timed_out:
            raise TimeoutError(f"SQL step timed out in session {self.name}")
        if not found:
            raise RuntimeError(f"mysql client exited during session {self.name}: {result['stdout']}")
        return result

    def close(self) -> None:
        try:
            if self.process.poll() is None:
                try:
                    assert self.process.stdin is not None
                    self.process.stdin.write("quit\n")
                    self.process.stdin.flush()
                    self.process.wait(timeout=5)
                except Exception:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=2)
        finally:
            if self.process.stdin is not None and not self.process.stdin.closed:
                self.process.stdin.close()
            self.reader.join(timeout=2)
            if self.process.stdout is not None and not self.process.stdout.closed:
                self.process.stdout.close()


def run_scenario(scenario_path: Path, manifest: dict, mysql_client: Path, evidence_dir: Path, timeout: int) -> dict:
    scenario = load_scenario(scenario_path)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    signals: dict[str, threading.Event] = {}
    session_results: dict[str, list[dict]] = {}
    errors: list[str] = []
    lock = threading.Lock()

    for sql_file in scenario.get("setup", {}).get("sql", []):
        content = (scenario_path.parent / sql_file).read_text(encoding="utf-8")
        result = _mysql(mysql_client, manifest["socket"], content, evidence_dir / f"setup-{Path(sql_file).stem}.json", timeout)
        if result["returncode"] != 0:
            raise RuntimeError(f"Setup SQL failed: {sql_file}")

    def event(name: str) -> threading.Event:
        with lock:
            return signals.setdefault(name, threading.Event())

    def worker(name: str, session: dict[str, Any]) -> None:
        local_results: list[dict] = []
        mysql_session: MysqlSession | None = None
        try:
            if any(next(iter(step)) in {"sql", "sql_file"} for step in session.get("steps", [])):
                mysql_session = MysqlSession(mysql_client, manifest["socket"], evidence_dir, name)
            for index, step in enumerate(session.get("steps", []), 1):
                action, value = next(iter(step.items()))
                if action == "signal":
                    event(str(value)).set()
                    local_results.append({"action": action, "value": value, "ok": True})
                elif action == "wait_for":
                    ok = event(str(value)).wait(timeout)
                    if not ok:
                        raise TimeoutError(f"Timeout waiting for signal {value}")
                    local_results.append({"action": action, "value": value, "ok": True})
                elif action == "sleep":
                    time.sleep(float(value))
                    local_results.append({"action": action, "value": value, "ok": True})
                elif action == "sql":
                    assert mysql_session is not None
                    local_results.append(mysql_session.execute(str(value), index, timeout))
                elif action == "sql_file":
                    assert mysql_session is not None
                    sql = (scenario_path.parent / str(value)).read_text(encoding="utf-8")
                    local_results.append(mysql_session.execute(sql, index, timeout))
        except Exception as exc:  # capture all session failures as evidence
            with lock:
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
        finally:
            if mysql_session:
                mysql_session.close()
            session_results[name] = local_results

    threads = [
        threading.Thread(target=worker, name=name, args=(name, session), daemon=True)
        for name, session in scenario.get("sessions", {}).items()
    ]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout
    for thread in threads:
        remaining = max(0.0, deadline - time.monotonic())
        thread.join(remaining)
    alive = [thread.name for thread in threads if thread.is_alive()]
    if alive:
        errors.append(f"Sessions timed out: {alive}")

    error_log = Path(manifest["error_log"])
    error_text = error_log.read_text(encoding="utf-8", errors="replace") if error_log.exists() else ""
    criteria = scenario.get("success_criteria", {})
    observations: dict[str, bool] = {}
    if "error_log_contains" in criteria:
        required_strings = criteria["error_log_contains"]
        observations["error_log_contains"] = bool(required_strings) and all(str(item) in error_text for item in required_strings)
    if "client_completed" in criteria:
        observations["client_completed"] = (not errors and not alive) == criteria["client_completed"]
    success = bool(observations) and all(observations.values()) and not alive
    result = {"success": success, "errors": errors, "sessions": session_results, "criteria": criteria, "observations": observations}
    (evidence_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
