from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required: python3 -m pip install PyYAML") from exc


DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "skill": {
        "name": "mysql-bug-analysis",
        "language": "zh-CN",
        "execution_mode": "automatic",
        "primary_version_family": "8.0",
    },
    "paths": {
        "source_root": "/data/mysql-source",
        "managed_source_root": "/data/mysql-source/managed",
        "build_root": "/data/mysql-build",
        "install_root": "/data/mysql-install",
        "runtime_root": "/data/mysql-bug-runtime",
        "workspace_root": "/data/mysql-bug-workspace",
        "report_root": "/data/mysql-bug-reports",
        "cache_root": "/data/mysql-bug-cache",
    },
    "source": {
        "layout": "per-version-directory",
        "local_directory_patterns": ["mysql-{version}", "mysql-server-{version}", "{version}"],
        "official_repository": "https://github.com/mysql/mysql-server.git",
        "clone_depth": 1,
        "allow_download": True,
        "preserve_existing_sources": True,
        "allow_instrument_existing_source": False,
    },
    "build": {
        "default_type": "Debug",
        "generator": "Ninja",
        "parallel_jobs": max(1, os.cpu_count() or 1),
        "clean_build": False,
        "reuse_existing_build": True,
        "install_after_build": True,
        "cmake_common_options": [
            "-DCMAKE_BUILD_TYPE=Debug",
            "-DWITH_DEBUG=1",
            "-DWITH_UNIT_TESTS=ON",
        ],
        "version_specific_options": {
            "5.7": ["-DDOWNLOAD_BOOST=1"],
            "8.0": [],
            "8.4": [],
        },
    },
    "runtime": {
        "mysql_user": "",
        "bind_address": "127.0.0.1",
        "port_range": {"start": 34060, "end": 34160},
        "initialize_mode": "initialize-insecure",
        "startup_timeout_seconds": 120,
        "shutdown_timeout_seconds": 60,
        "reproduction_timeout_seconds": 600,
        "default_server_options": ["--skip-name-resolve"],
        "enable_core_dump": True,
        "cleanup_after_success": False,
        "cleanup_after_failure": False,
    },
    "debug": {
        "debugger": "gdb",
        "gdb_path": "/usr/bin/gdb",
        "batch_mode": True,
        "enable_pretty_printing": True,
        "collect_all_thread_backtraces": True,
        "collect_full_backtraces": True,
        "enable_sanitizers": False,
        "allowed_sanitizers": ["address", "undefined", "thread"],
        "allow_source_instrumentation": True,
        "allow_dbug_injection": True,
        "allow_debug_sync": True,
        "allow_fault_injection": False,
    },
    "research": {
        "official_sources_only_for_final_conclusions": True,
        "allow_secondary_sources_as_leads": True,
        "save_web_evidence": True,
        "save_release_notes": True,
        "save_bug_page": True,
        "save_commit_diff": True,
    },
    "reports": {
        "format": "markdown",
        "output_files": {
            "analysis": "BUG-{bug_id}-analysis.md",
            "reproduction": "BUG-{bug_id}-reproduction.md",
        },
        "include_command_output": True,
        "include_failed_attempts": True,
        "include_evidence_index": True,
        "include_absolute_paths": True,
        "redact_secrets": True,
    },
    "safety": {
        "require_ownership_marker": True,
        "ownership_marker": ".mysql-bug-skill-owned",
        "prohibit_existing_instance_datadir": True,
        "prohibit_system_mysql_service_changes": True,
        "prohibit_package_removal": True,
        "prohibit_firewall_changes": True,
        "prohibit_selinux_disable": True,
        "prohibit_app_armor_disable": True,
        "allow_dependency_installation": False,
        "allow_root_commands": False,
        "disk_free_minimum_gb": 30,
        "memory_free_minimum_gb": 4,
    },
    "logging": {"level": "INFO", "command_log": True, "environment_log": True, "timestamps": True},
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def discover_config(explicit: str | Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env_value = os.getenv("MYSQL_BUG_SKILL_CONFIG")
    if env_value:
        candidates.append(Path(env_value).expanduser())
    candidates.extend([
        Path.cwd() / "mysql-bug-skill.yaml",
        Path.home() / ".codex" / "mysql-bug-skill.yaml",
    ])
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def load_config(path: str | Path | None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    resolved = discover_config(path)
    if path is not None and resolved is None:
        raise FileNotFoundError(f"Configuration file not found: {path}")
    if resolved:
        loaded = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError("YAML root must be a mapping")
        config = deep_merge(config, loaded)
        config["_config_file"] = str(resolved)
    if overrides:
        config = deep_merge(config, overrides)
    return config


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    paths = config.get("paths", {})
    required = [
        "source_root", "managed_source_root", "build_root", "install_root",
        "runtime_root", "workspace_root", "report_root", "cache_root",
    ]
    resolved: dict[str, Path] = {}
    for key in required:
        value = paths.get(key)
        if not value:
            raise ValueError(f"Missing paths.{key}")
        path = Path(str(value)).expanduser()
        if not path.is_absolute():
            raise ValueError(f"paths.{key} must be absolute: {value}")
        resolved[key] = path.resolve(strict=False)

    dangerous = {Path("/"), Path("/var/lib/mysql"), Path("/var/lib/mysqld"), Path("/usr"), Path("/etc")}
    for key in ("runtime_root", "workspace_root", "build_root", "install_root", "managed_source_root"):
        if resolved[key] in dangerous:
            raise ValueError(f"Dangerous managed path rejected: paths.{key}={resolved[key]}")

    if resolved["runtime_root"] == resolved["source_root"]:
        raise ValueError("runtime_root and source_root must differ")
    if resolved["managed_source_root"] == resolved["source_root"]:
        raise ValueError("managed_source_root must be a child or separate managed directory")

    port_range = config.get("runtime", {}).get("port_range", {})
    start, end = int(port_range.get("start", 0)), int(port_range.get("end", 0))
    if not (1024 <= start <= end <= 65535):
        raise ValueError(f"Invalid runtime.port_range: {start}-{end}")

    marker = config.get("safety", {}).get("ownership_marker", "")
    if not marker or "/" in marker or marker in {".", ".."}:
        raise ValueError("Invalid safety.ownership_marker")
    return config
