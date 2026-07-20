from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import resource
from pathlib import Path
from typing import Any

from .command import run_command

_VERSION_PATTERNS = {
    "major": re.compile(r"MYSQL_VERSION_MAJOR\s+([0-9]+)", re.I),
    "minor": re.compile(r"MYSQL_VERSION_MINOR\s+([0-9]+)", re.I),
    "patch": re.compile(r"MYSQL_VERSION_PATCH\s+([0-9]+)", re.I),
    "extra": re.compile(r"MYSQL_VERSION_EXTRA\s+\"?([^\")\s]*)", re.I),
}


def parse_mysql_version(text: str) -> str | None:
    values: dict[str, str] = {}
    for key, pattern in _VERSION_PATTERNS.items():
        match = pattern.search(text)
        if match:
            values[key] = match.group(1)
    if not all(k in values for k in ("major", "minor", "patch")):
        return None
    version = f"{values['major']}.{values['minor']}.{values['patch']}"
    extra = values.get("extra", "").strip()
    return version + extra if extra else version


def _git_value(source: Path, args: list[str]) -> str | None:
    if not (source / ".git").exists():
        return None
    try:
        return subprocess.check_output(["git", "-C", str(source), *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def inspect_source_tree(path: Path, managed: bool) -> dict[str, Any]:
    version_file = path / "MYSQL_VERSION"
    version = parse_mysql_version(version_file.read_text(encoding="utf-8", errors="replace")) if version_file.is_file() else None
    valid = bool(version and (path / "CMakeLists.txt").is_file() and (path / "sql").is_dir())
    status = _git_value(path, ["status", "--porcelain"])
    return {
        "path": str(path.resolve()),
        "version": version,
        "valid_source_tree": valid,
        "managed": managed,
        "writable": os.access(path, os.W_OK),
        "git_repository": (path / ".git").exists(),
        "commit": _git_value(path, ["rev-parse", "HEAD"]),
        "branch": _git_value(path, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": bool(status),
    }


def scan_source_trees(root: Path, managed: bool) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        info = inspect_source_tree(child, managed)
        if info["version"] or info["valid_source_tree"]:
            items.append(info)
    return items


def _tool_info(name: str, version_args: list[str] | None = None) -> dict[str, Any]:
    path = shutil.which(name)
    result: dict[str, Any] = {"name": name, "path": path, "available": bool(path)}
    if path:
        args = [path] + (version_args or ["--version"])
        run = run_command(args, timeout=10)
        first = (run["stdout"] or run["stderr"]).splitlines()
        result["version"] = first[0] if first else ""
    return result



def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, PermissionError):
        return None


def _memory_info() -> dict[str, Any]:
    values: dict[str, int] = {}
    text = _read_text(Path("/proc/meminfo")) or ""
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        match = re.search(r"(\d+)", raw)
        if match:
            values[key] = int(match.group(1)) * 1024
    return {
        "total_bytes": values.get("MemTotal"),
        "available_bytes": values.get("MemAvailable"),
        "swap_total_bytes": values.get("SwapTotal"),
        "swap_free_bytes": values.get("SwapFree"),
    }


def _existing_parent(path: Path) -> Path:
    current = path.expanduser().resolve(strict=False)
    while not current.exists() and current != current.parent:
        current = current.parent
    return current


def _disk_info(config: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, value in config.get("paths", {}).items():
        path = Path(str(value))
        base = _existing_parent(path)
        try:
            usage = shutil.disk_usage(base)
            result[key] = {
                "configured_path": str(path),
                "measured_path": str(base),
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
            }
        except OSError as exc:
            result[key] = {"configured_path": str(path), "error": str(exc)}
    return result


def _running_mysql() -> list[str]:
    pgrep = shutil.which("pgrep")
    if not pgrep:
        return []
    result = run_command([pgrep, "-a", "mysqld"], timeout=10)
    if result["returncode"] not in (0, 1):
        return []
    return [line for line in result["stdout"].splitlines() if line.strip()]


def _limits() -> dict[str, Any]:
    names = {
        "core": resource.RLIMIT_CORE,
        "nofile": resource.RLIMIT_NOFILE,
        "nproc": getattr(resource, "RLIMIT_NPROC", resource.RLIMIT_NOFILE),
        "as": resource.RLIMIT_AS,
    }
    return {name: {"soft": resource.getrlimit(value)[0], "hard": resource.getrlimit(value)[1]} for name, value in names.items()}

def discover_environment(config: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_root = Path(config["paths"]["source_root"])
    managed_root = Path(config["paths"]["managed_source_root"])
    tools = [_tool_info(name) for name in ["git", "cmake", "ninja", "make", "gcc", "g++", "gdb", "python3", "ss"]]
    sources = scan_source_trees(source_root, managed=False)
    if managed_root.resolve(strict=False) != source_root.resolve(strict=False):
        sources.extend(scan_source_trees(managed_root, managed=True))
    memory = _memory_info()
    disk = _disk_info(config)
    minimum_disk = int(config.get("safety", {}).get("disk_free_minimum_gb", 0)) * 1024**3
    minimum_memory = int(config.get("safety", {}).get("memory_free_minimum_gb", 0)) * 1024**3
    environment = {
        "system": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "os_release": _read_text(Path("/etc/os-release")),
        },
        "resources": {
            "memory": memory,
            "disk": disk,
            "limits": _limits(),
            "thresholds": {
                "minimum_disk_free_bytes": minimum_disk,
                "minimum_memory_available_bytes": minimum_memory,
                "memory_sufficient": memory.get("available_bytes") is None or memory.get("available_bytes", 0) >= minimum_memory,
                "disk_sufficient": all(item.get("free_bytes", minimum_disk) >= minimum_disk for item in disk.values()),
            },
        },
        "debug": {
            "core_pattern": _read_text(Path("/proc/sys/kernel/core_pattern")),
            "ptrace_scope": _read_text(Path("/proc/sys/kernel/yama/ptrace_scope")),
            "aslr": _read_text(Path("/proc/sys/kernel/randomize_va_space")),
        },
        "running_mysql": _running_mysql(),
        "tools": tools,
        "sources": sources,
    }
    (output_dir / "environment.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "source-inventory.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    return environment
