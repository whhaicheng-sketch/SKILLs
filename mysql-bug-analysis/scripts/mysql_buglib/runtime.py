from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

from .command import run_command
from .safety import allocate_port, create_owned_dir, require_owned


def _normalize_option(option: str) -> str:
    return option[2:] if option.startswith("--") else option


def generate_my_cnf(*, basedir: Path, instance_dir: Path, port: int, bind_address: str, extra_options: list[str]) -> Path:
    data = instance_dir / "data"
    log = instance_dir / "log"
    tmp = instance_dir / "tmp"
    for p in (data, log, tmp):
        p.mkdir(parents=True, exist_ok=True)
    lines = [
        "[mysqld]",
        f"basedir={basedir}",
        f"datadir={data}",
        f"socket={instance_dir / 'mysql.sock'}",
        f"port={port}",
        f"bind-address={bind_address}",
        f"pid-file={instance_dir / 'mysqld.pid'}",
        f"log-error={log / 'error.log'}",
        f"tmpdir={tmp}",
        "skip-name-resolve",
    ]
    lines.extend(_normalize_option(x) for x in extra_options if _normalize_option(x) != "skip-name-resolve")
    path = instance_dir / "my.cnf"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def prepare_instance(config: dict, bug_id: str, version: str, role: str, install_dir: Path, mysqld: Path, extra_options: list[str] | None = None) -> dict:
    marker = config["safety"]["ownership_marker"]
    runtime_root = Path(config["paths"]["runtime_root"])
    bug_runtime = runtime_root / f"BUG-{bug_id}"
    create_owned_dir(bug_runtime, marker)
    instance_dir = bug_runtime / f"{version}-{role}"
    create_owned_dir(instance_dir, marker)
    port_cfg = config["runtime"]["port_range"]
    port = allocate_port(config["runtime"]["bind_address"], int(port_cfg["start"]), int(port_cfg["end"]))
    cnf = generate_my_cnf(
        basedir=install_dir, instance_dir=instance_dir, port=port,
        bind_address=config["runtime"]["bind_address"],
        extra_options=list(config["runtime"].get("default_server_options", [])) + list(extra_options or []),
    )
    data = instance_dir / "data"
    if not any(data.iterdir()):
        mode = config["runtime"].get("initialize_mode", "initialize-insecure")
        args = [str(mysqld), f"--defaults-file={cnf}", f"--{mode}"]
        run_command(args, timeout=600, log_path=instance_dir / "initialize.json", check=True)
    manifest = {
        "instance_id": f"BUG-{bug_id}-{version}-{role}", "bug_id": str(bug_id),
        "version": version, "role": role, "instance_dir": str(instance_dir),
        "install_dir": str(install_dir), "mysqld": str(mysqld), "my_cnf": str(cnf),
        "port": port, "socket": str(instance_dir / "mysql.sock"),
        "datadir": str(data), "pid_file": str(instance_dir / "mysqld.pid"),
        "error_log": str(instance_dir / "log" / "error.log"),
    }
    (instance_dir / "instance.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _pid(manifest: dict) -> int | None:
    path = Path(manifest["pid_file"])
    if not path.is_file():
        return None
    try:
        return int(path.read_text().strip())
    except ValueError:
        return None


def process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False



def pid_matches_executable(pid: int, expected: Path) -> bool:
    """Verify a PID still belongs to the exact mysqld binary from the manifest."""
    if pid <= 0:
        return False
    expected_resolved = expected.expanduser().resolve(strict=False)
    proc_exe = Path(f"/proc/{pid}/exe")
    try:
        return proc_exe.resolve(strict=True) == expected_resolved
    except (FileNotFoundError, PermissionError, OSError):
        cmdline = Path(f"/proc/{pid}/cmdline")
        try:
            first = cmdline.read_bytes().split(b"\0", 1)[0].decode(errors="replace")
            return Path(first).resolve(strict=False) == expected_resolved
        except (FileNotFoundError, PermissionError, OSError):
            return False

def start_instance(manifest: dict, timeout: int = 120, under_gdb: bool = False) -> dict:
    instance_dir = Path(manifest["instance_dir"])
    existing_pid = _pid(manifest)
    if process_alive(existing_pid):
        if not pid_matches_executable(existing_pid, Path(manifest["mysqld"])):
            raise PermissionError(f"PID file points to a different executable: {existing_pid}")
        return {"started": False, "already_running": True, "pid": existing_pid}
    cmd = [manifest["mysqld"], f"--defaults-file={manifest['my_cnf']}"]
    stdout = (instance_dir / "mysqld.stdout.log").open("ab")
    stderr = (instance_dir / "mysqld.stderr.log").open("ab")
    try:
        proc = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, start_new_session=True)
    finally:
        stdout.close()
        stderr.close()
    deadline = time.time() + timeout
    while time.time() < deadline:
        pid = _pid(manifest)
        if process_alive(pid) and Path(manifest["socket"]).exists():
            return {"started": True, "pid": pid, "launcher_pid": proc.pid}
        if proc.poll() is not None:
            break
        time.sleep(0.5)
    raise RuntimeError(f"mysqld failed to start; see {manifest['error_log']}")


def stop_instance(manifest: dict, mysqladmin: Path | None = None, timeout: int = 60) -> dict:
    pid = _pid(manifest)
    if not process_alive(pid):
        return {"stopped": False, "already_stopped": True}
    if not pid_matches_executable(pid, Path(manifest["mysqld"])):
        raise PermissionError(f"Refusing to stop PID {pid}: executable does not match manifest")
    if mysqladmin and mysqladmin.is_file():
        run_command([str(mysqladmin), f"--socket={manifest['socket']}", "-uroot", "shutdown"], timeout=timeout)
    deadline = time.time() + timeout
    while time.time() < deadline and process_alive(pid):
        time.sleep(0.5)
    if process_alive(pid):
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
    if process_alive(pid):
        os.kill(pid, signal.SIGKILL)
    return {"stopped": True, "pid": pid}


def baseline(manifest: dict, mysql_client: Path, evidence_dir: Path) -> dict:
    sql = "SELECT VERSION(); CREATE DATABASE IF NOT EXISTS bug_skill_baseline; CREATE TABLE IF NOT EXISTS bug_skill_baseline.t(id INT PRIMARY KEY); DROP DATABASE bug_skill_baseline;"
    result = run_command([str(mysql_client), f"--socket={manifest['socket']}", "-uroot", "-e", sql], timeout=60, log_path=evidence_dir / "baseline.json")
    if result["returncode"] != 0:
        raise RuntimeError("Baseline failed")
    return result
