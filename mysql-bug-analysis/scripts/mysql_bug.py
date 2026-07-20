#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mysql_buglib.build import build_mysql
from mysql_buglib.command import run_command
from mysql_buglib.confidence import evaluate_confidence
from mysql_buglib.config import load_config, validate_config
from mysql_buglib.debug import run_gdb
from mysql_buglib.discovery import discover_environment
from mysql_buglib.evidence import collect_file
from mysql_buglib.mtr import run_mtr
from mysql_buglib.quality import report_check
from mysql_buglib.reports import render_reports, report_artifact_id
from mysql_buglib.reproduce import run_scenario
from mysql_buglib.research import research_bug
from mysql_buglib.result import emit, fail
from mysql_buglib.runtime import baseline, prepare_instance, start_instance, stop_instance
from mysql_buglib.safety import safe_remove_tree
from mysql_buglib.source import acquire_source, find_local_source, create_instrumentation_copy
from mysql_buglib.source_diff import source_diff
from mysql_buglib.state import PHASES, TaskState
from mysql_buglib.validation import validate_fix
from mysql_buglib.versions import resolve_version_roles
from mysql_buglib.discovery import scan_source_trees
from mysql_buglib.workspace import create_workspace, normalize_bug_id, workspace_path

SKILL_ROOT = SCRIPT_DIR.parent
ASSETS_DIR = SKILL_ROOT / "assets"


def _cfg(args: argparse.Namespace) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if getattr(args, "source_root", None):
        overrides.setdefault("paths", {})["source_root"] = args.source_root
    config = load_config(getattr(args, "config", None), overrides=overrides)
    return validate_config(config)


def _workspace(config: dict, bug_id: str, create: bool = True) -> Path:
    root = Path(config["paths"]["workspace_root"])
    if create:
        return create_workspace(root, bug_id, config["safety"]["ownership_marker"])
    return workspace_path(root, bug_id)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _state(workspace: Path) -> TaskState:
    path = workspace / "state.json"
    return TaskState.load(path) if path.exists() else TaskState.create(workspace.name, path)


def _mysql_client(manifest: dict) -> Path:
    install = Path(manifest["install_dir"])
    candidates = [install / "bin" / "mysql", install / "bin" / "mysqladmin"]
    client = candidates[0]
    if not client.is_file():
        found = shutil.which("mysql")
        if not found:
            raise FileNotFoundError("mysql client not found in install_dir or PATH")
        client = Path(found)
    return client


def cmd_config_check(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        return emit("config-check", True, {"config_file": config.get("_config_file"), "paths": config["paths"]}, next_action="init-task")
    except Exception as exc:
        return fail("config-check", exc)


def cmd_init_task(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        bug_id = normalize_bug_id(args.bug_id)
        workspace = _workspace(config, bug_id)
        metadata = _load_json(workspace / "metadata.json")
        metadata.update({"bug_id": bug_id})
        if args.description:
            metadata["description"] = args.description
        if args.title:
            metadata["title"] = args.title
        _write_json(workspace / "metadata.json", metadata)
        task = {"bug_id": bug_id, "description": args.description or "", "bug_url": args.bug_url or ""}
        import yaml
        (workspace / "task.yaml").write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return emit("init-task", True, {"bug_id": bug_id, "workspace": str(workspace)}, artifacts=[str(workspace / "state.json"), str(workspace / "metadata.json")], next_action="discover")
    except Exception as exc:
        return fail("init-task", exc, phase="DISCOVER")


def cmd_discover(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        result = discover_environment(config, workspace / "evidence" / "runtime" / "environment")
        _state(workspace).complete_phase("DISCOVER")
        return emit("discover", True, result, phase="DISCOVER", artifacts=[str(workspace / "evidence" / "runtime" / "environment" / "environment.json")], next_action="research")
    except Exception as exc:
        return fail("discover", exc, phase="DISCOVER")


def cmd_research(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        result = research_bug(args.bug_id, workspace / "evidence" / "official", args.bug_url)
        metadata = _load_json(workspace / "metadata.json")
        if result.get("title"):
            metadata.setdefault("title", result["title"])
        metadata["official_bug_url"] = result.get("official_url")
        metadata["official_research"] = result
        _write_json(workspace / "metadata.json", metadata)
        _state(workspace).complete_phase("RESEARCH")
        return emit("research", True, result, phase="RESEARCH", artifacts=[str(workspace / "evidence" / "official" / "bug-page.html")], next_action="resolve-versions")
    except Exception as exc:
        return fail("research", exc, phase="RESEARCH", next_action="preserve official evidence manually and continue")



def cmd_resolve_versions(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        research_path = workspace / "evidence" / "official" / "research-summary.json"
        research = _load_json(research_path) if research_path.is_file() else {}
        sources = scan_source_trees(Path(config["paths"]["source_root"]), managed=False)
        sources += scan_source_trees(Path(config["paths"]["managed_source_root"]), managed=True)
        local_versions = [item["version"] for item in sources if item.get("version")]
        result = resolve_version_roles(research=research, local_versions=local_versions, affected=args.affected_version, fixed=args.fixed_version)
        evidence = workspace / "evidence" / "source" / "version-matrix.json"
        _write_json(evidence, result)
        metadata = _load_json(workspace / "metadata.json")
        if result.get("recommended_affected_version"):
            metadata["affected_versions"] = [result["recommended_affected_version"]]
        if result.get("recommended_fixed_version"):
            metadata["fixed_versions"] = [result["recommended_fixed_version"]]
        _write_json(workspace / "metadata.json", metadata)
        success = bool(result.get("recommended_affected_version"))
        if success:
            _state(workspace).complete_phase("VERSION_RESOLUTION")
        return emit("resolve-versions", success, result, phase="VERSION_RESOLUTION", artifacts=[str(evidence)], next_action="acquire-source" if success else "provide affected version or inspect official evidence")
    except Exception as exc:
        return fail("resolve-versions", exc, phase="VERSION_RESOLUTION")


def cmd_instrument_copy(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        source = _resolve_source(config, args.version, args.source_dir)
        target = create_instrumentation_copy(config, source, normalize_bug_id(args.bug_id), args.version)
        manifest = {"version": args.version, "original_source": str(source), "instrumentation_source": str(target)}
        out = workspace / "evidence" / "source" / f"instrumentation-copy-{args.version}.json"
        _write_json(out, manifest)
        return emit("instrument-copy", True, manifest, phase="DEBUG", artifacts=[str(out)], next_action="apply and preserve a minimal patch")
    except Exception as exc:
        return fail("instrument-copy", exc, phase="DEBUG")


def cmd_validate_fix(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        affected = _load_json(Path(args.affected_manifest))
        fixed = _load_json(Path(args.fixed_manifest))
        affected_client = _mysql_client(affected)
        fixed_client = _mysql_client(fixed)
        evidence = workspace / "evidence" / "runtime" / "fix-validation"
        result = validate_fix(Path(args.scenario), affected, fixed, affected_client, fixed_client, evidence, iterations=args.iterations, timeout=args.timeout, path_coverage_artifact=Path(args.path_coverage_artifact) if args.path_coverage_artifact else None)
        state = _state(workspace)
        state.update(fix_validated=bool(result["validated"]))
        if result["validated"]:
            state.complete_phase("FIX_VALIDATION")
        metadata = _load_json(workspace / "metadata.json")
        metadata["fix_validation_status"] = "validated" if result["validated"] else "not-validated"
        metadata["affected_versions"] = [affected.get("version")]
        metadata["fixed_versions"] = [fixed.get("version")]
        _write_json(workspace / "metadata.json", metadata)
        return emit("validate-fix", result["validated"], result, phase="FIX_VALIDATION", artifacts=[str(evidence / "fix-validation.json")], next_action="source-analysis-and-confidence")
    except Exception as exc:
        return fail("validate-fix", exc, phase="FIX_VALIDATION")

def cmd_acquire_source(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        result = acquire_source(config, args.version, workspace / "evidence" / "source" / args.version)
        return emit("acquire-source", True, result, phase="VERSION_RESOLUTION", artifacts=[str(workspace / "evidence" / "source" / args.version / f"source-{args.version}.json")], next_action="build")
    except Exception as exc:
        return fail("acquire-source", exc, phase="VERSION_RESOLUTION")


def _resolve_source(config: dict, version: str, explicit: str | None) -> Path:
    if explicit:
        source = Path(explicit).expanduser().resolve()
        if not source.is_dir():
            raise FileNotFoundError(source)
        return source
    source = find_local_source(Path(config["paths"]["source_root"]), version)
    if source is None:
        source = find_local_source(Path(config["paths"]["managed_source_root"]), version)
    if source is None:
        raise FileNotFoundError(f"Source for MySQL {version} not found; run acquire-source")
    return source


def cmd_build(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        source = _resolve_source(config, args.version, args.source_dir)
        evidence = workspace / "evidence" / "build" / f"{args.version}-{args.role}"
        result = build_mysql(config, source, args.version, args.role, evidence, clean=args.clean)
        return emit("build", True, result, phase="PREPARE", artifacts=[str(evidence / "build-manifest.json")], next_action="prepare-instance")
    except Exception as exc:
        return fail("build", exc, phase="PREPARE")


def cmd_prepare_instance(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        build_manifest = _load_json(Path(args.build_manifest))
        result = prepare_instance(config, args.bug_id, args.version, args.role, Path(build_manifest["install_dir"]), Path(build_manifest["mysqld"]), args.server_option)
        manifest_path = Path(result["instance_dir"]) / "instance.json"
        copied = workspace / "evidence" / "runtime" / f"instance-{args.version}-{args.role}.json"
        _write_json(copied, result)
        _state(workspace).complete_phase("PREPARE")
        return emit("prepare-instance", True, result, phase="PREPARE", artifacts=[str(manifest_path), str(copied)], next_action="start")
    except Exception as exc:
        return fail("prepare-instance", exc, phase="PREPARE")


def cmd_start(args: argparse.Namespace) -> int:
    try:
        manifest = _load_json(Path(args.instance_manifest))
        result = start_instance(manifest, timeout=args.timeout)
        return emit("start", True, result, artifacts=[manifest["error_log"]], next_action="baseline")
    except Exception as exc:
        return fail("start", exc)


def cmd_stop(args: argparse.Namespace) -> int:
    try:
        manifest = _load_json(Path(args.instance_manifest))
        mysqladmin = Path(manifest["install_dir"]) / "bin" / "mysqladmin"
        result = stop_instance(manifest, mysqladmin=mysqladmin, timeout=args.timeout)
        return emit("stop", True, result)
    except Exception as exc:
        return fail("stop", exc)


def cmd_baseline(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        manifest = _load_json(Path(args.instance_manifest))
        result = baseline(manifest, _mysql_client(manifest), workspace / "evidence" / "runtime" / f"baseline-{manifest['version']}-{manifest['role']}")
        _state(workspace).complete_phase("BASELINE")
        return emit("baseline", True, result, phase="BASELINE", next_action="reproduce")
    except Exception as exc:
        return fail("baseline", exc, phase="BASELINE")


def cmd_reproduce(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        manifest = _load_json(Path(args.instance_manifest))
        timeout = args.timeout or int(config["runtime"]["reproduction_timeout_seconds"])
        evidence = workspace / "evidence" / "runtime" / f"reproduce-{manifest['version']}-{manifest['role']}"
        result = run_scenario(Path(args.scenario), manifest, _mysql_client(manifest), evidence, timeout)
        state = _state(workspace)
        if result["success"]:
            state.update(reproduced=True)
        if result["success"]:
            state.complete_phase("REPRODUCE")
        return emit("reproduce", result["success"], result, phase="REPRODUCE", artifacts=[str(evidence / "result.json")], next_action="gdb" if result["success"] else "mtr-or-instrument")
    except Exception as exc:
        return fail("reproduce", exc, phase="REPRODUCE")


def cmd_mtr(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        result = run_mtr(Path(args.source_dir), args.test, workspace / "evidence" / "mtr", Path(args.build_dir) if args.build_dir else None, args.mtr_arg, args.timeout)
        return emit("mtr", result["success"], result, phase="REPRODUCE", next_action="debug-or-source-analysis")
    except Exception as exc:
        return fail("mtr", exc, phase="REPRODUCE")


def cmd_gdb(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        manifest = _load_json(Path(args.instance_manifest)) if args.instance_manifest else None
        mysqld = Path(args.mysqld or manifest["mysqld"])
        defaults = Path(manifest["my_cnf"]) if manifest and args.mode == "launch" else None
        pid = None
        if args.mode == "attach":
            if args.pid:
                pid = args.pid
            elif manifest:
                pid = int(Path(manifest["pid_file"]).read_text().strip())
        evidence = workspace / "evidence" / ("core" if args.mode == "core" else "gdb") / args.mode
        result = run_gdb(gdb_path=Path(config["debug"]["gdb_path"]), mode=args.mode, mysqld=mysqld, evidence_dir=evidence, defaults_file=defaults, pid=pid, core_file=Path(args.core_file) if args.core_file else None, commands_file=Path(args.commands) if args.commands else None, breakpoints=args.breakpoint, timeout=args.timeout)
        if result["success"]:
            _state(workspace).complete_phase("DEBUG")
        return emit("gdb", result["success"], result, phase="DEBUG", artifacts=[str(evidence / "gdb-session.log")], next_action="source-analysis")
    except Exception as exc:
        return fail("gdb", exc, phase="DEBUG")


def cmd_source_diff(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        result = source_diff(Path(args.before), Path(args.after), workspace / "evidence" / "patch", args.path, args.timeout)
        success = result.get("returncode") in (0, 1)
        if success:
            _state(workspace).complete_phase("SOURCE_ANALYSIS")
        return emit("source-diff", success, result, phase="SOURCE_ANALYSIS", artifacts=[result["diff"]], next_action="validate-fix" if success else "inspect diff execution error")
    except Exception as exc:
        return fail("source-diff", exc, phase="SOURCE_ANALYSIS")


def cmd_collect(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        destination = workspace / "evidence" / args.category
        result = collect_file(Path(args.file), destination, args.category, args.description or "")
        return emit("collect", True, result, artifacts=[result["path"]])
    except Exception as exc:
        return fail("collect", exc)


def _has_files(path: Path, patterns: tuple[str, ...] = ("*",)) -> bool:
    return any(item.is_file() for pattern in patterns for item in path.rglob(pattern)) if path.exists() else False


def _derive_evidence(workspace: Path, metadata: dict, state: dict) -> dict:
    source_root = workspace / "evidence" / "source"
    source_analysis_files = ("*root-cause*", "*call-chain*", "*fix-analysis*", "*.patch", "*.diff", "*.md")
    return {
        "reproduced": bool(state.get("reproduced") or metadata.get("reproduction_status") == "reproduced"),
        "fix_validated": bool(state.get("fix_validated") or metadata.get("fix_validation_status") == "validated"),
        "dynamic_evidence": _has_files(workspace / "evidence" / "gdb") or _has_files(workspace / "evidence" / "core"),
        "source_evidence": bool(metadata.get("source_analysis_complete")) or _has_files(source_root, source_analysis_files),
        "official_evidence": bool(metadata.get("official_evidence_reviewed")),
        "official_fix_test_evidence": bool(metadata.get("official_fix_test_evidence")),
        "patch_evidence": bool(metadata.get("patch_analysis_complete")) or _has_files(workspace / "evidence" / "patch", ("*.patch", "*.diff", "source.diff")),
        "mtr_or_fault_injection": _has_files(workspace / "evidence" / "mtr") or bool(metadata.get("fault_injection_used")),
    }


def cmd_confidence(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        metadata = _load_json(workspace / "metadata.json")
        state_obj = _state(workspace)
        evidence = _derive_evidence(workspace, metadata, state_obj.data)
        evidence.update({key: True for key in args.flag})
        result = evaluate_confidence(evidence)
        metadata["confidence_level"] = result["level"]
        metadata["confidence_reason"] = result["reason"]
        _write_json(workspace / "metadata.json", metadata)
        state_obj.update(confidence_level=result["level"])
        state_obj.complete_phase("CONCLUSION")
        return emit("confidence", True, {**result, "evidence": evidence}, phase="CONCLUSION", next_action="report")
    except Exception as exc:
        return fail("confidence", exc, phase="CONCLUSION")


def cmd_report(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id)
        outputs = render_reports(workspace, Path(config["paths"]["report_root"]), ASSETS_DIR, force=args.force)
        return emit("report", True, outputs, phase="REPORT", artifacts=list(outputs.values()), next_action="edit reports and run report-check")
    except Exception as exc:
        return fail("report", exc, phase="REPORT")


def cmd_report_check(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        bug_id = normalize_bug_id(args.bug_id)
        artifact_id = report_artifact_id(bug_id)
        report_dir = Path(config["paths"]["report_root"]) / artifact_id
        result = report_check(report_dir, artifact_id.removeprefix("BUG-"))
        if result["success"]:
            _state(_workspace(config, bug_id)).complete_phase("REPORT")
        return emit("report-check", result["success"], result, phase="REPORT", next_action=None if result["success"] else "complete unresolved report sections")
    except Exception as exc:
        return fail("report-check", exc, phase="REPORT")


def cmd_status(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id, create=False)
        result = {"workspace": str(workspace), "state": _load_json(workspace / "state.json"), "metadata": _load_json(workspace / "metadata.json")}
        return emit("status", True, result)
    except Exception as exc:
        return fail("status", exc)


def cmd_skip_phase(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        workspace = _workspace(config, args.bug_id, create=False)
        state = _state(workspace)
        state.skip_phase(args.phase, args.reason)
        return emit("skip-phase", True, {"phase": args.phase, "reason": args.reason}, next_action=state.data["phase"])
    except Exception as exc:
        return fail("skip-phase", exc, phase=args.phase)


def cmd_cleanup(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        marker = config["safety"]["ownership_marker"]
        bug_id = normalize_bug_id(args.bug_id)
        if args.target == "workspace":
            root = Path(config["paths"]["workspace_root"])
            target = workspace_path(root, bug_id)
        elif args.target == "runtime":
            root = Path(config["paths"]["runtime_root"])
            target = root / f"BUG-{bug_id}"
        else:
            raise ValueError("Unsupported cleanup target")
        safe_remove_tree(target, root, marker)
        return emit("cleanup", True, {"removed": str(target)})
    except Exception as exc:
        return fail("cleanup", exc)


def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        config = _cfg(args)
        bug_id = normalize_bug_id(args.bug_id)
        workspace = _workspace(config, bug_id)
        metadata = _load_json(workspace / "metadata.json")
        metadata.update({"bug_id": bug_id})
        if args.description:
            metadata["description"] = args.description
        if args.title:
            metadata["title"] = args.title
        _write_json(workspace / "metadata.json", metadata)
        task = {"bug_id": bug_id, "description": args.description or "", "bug_url": args.bug_url or ""}
        import yaml
        (workspace / "task.yaml").write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False), encoding="utf-8")
        environment = discover_environment(config, workspace / "evidence" / "runtime" / "environment")
        state = _state(workspace)
        state.complete_phase("DISCOVER")
        warnings = []
        research = None
        if bug_id.isdigit() or args.bug_url:
            try:
                research = research_bug(bug_id, workspace / "evidence" / "official", args.bug_url)
                state.complete_phase("RESEARCH")
                metadata = _load_json(workspace / "metadata.json")
                metadata["official_research"] = research
                metadata["official_bug_url"] = research.get("official_url")
                if research.get("title"):
                    metadata.setdefault("title", research["title"])
                _write_json(workspace / "metadata.json", metadata)
            except Exception as exc:
                warnings.append(f"Official BUG fetch failed: {type(exc).__name__}: {exc}")
        else:
            warnings.append("Local task has no official BUG ID; search official sources from the symptom and supplied artifacts.")
        result = {"bug_id": bug_id, "workspace": str(workspace), "environment": environment, "research": research}
        return emit("analyze", True, result, phase=state.data.get("phase"), warnings=warnings, artifacts=[str(workspace / "state.json"), str(workspace / "metadata.json")], next_action="resolve-versions")
    except Exception as exc:
        return fail("analyze", exc, phase="DISCOVER")


def add_common(parser: argparse.ArgumentParser, bug_id: bool = True) -> None:
    parser.add_argument("--config")
    parser.add_argument("--source-root")
    if bug_id:
        parser.add_argument("--bug-id", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic runner for the mysql-bug-analysis Codex skill")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("config-check"); add_common(p, False); p.set_defaults(func=cmd_config_check)
    p = sub.add_parser("init-task"); add_common(p); p.add_argument("--description"); p.add_argument("--title"); p.add_argument("--bug-url"); p.set_defaults(func=cmd_init_task)
    p = sub.add_parser("discover"); add_common(p); p.set_defaults(func=cmd_discover)
    p = sub.add_parser("research"); add_common(p); p.add_argument("--bug-url"); p.set_defaults(func=cmd_research)
    p = sub.add_parser("resolve-versions"); add_common(p); p.add_argument("--affected-version"); p.add_argument("--fixed-version"); p.set_defaults(func=cmd_resolve_versions)
    p = sub.add_parser("acquire-source"); add_common(p); p.add_argument("--version", required=True); p.set_defaults(func=cmd_acquire_source)
    p = sub.add_parser("instrument-copy"); add_common(p); p.add_argument("--version", required=True); p.add_argument("--source-dir"); p.set_defaults(func=cmd_instrument_copy)
    p = sub.add_parser("build"); add_common(p); p.add_argument("--version", required=True); p.add_argument("--role", choices=["affected", "fixed", "good", "bad"], required=True); p.add_argument("--source-dir"); p.add_argument("--clean", action="store_true"); p.set_defaults(func=cmd_build)
    p = sub.add_parser("prepare-instance"); add_common(p); p.add_argument("--version", required=True); p.add_argument("--role", required=True); p.add_argument("--build-manifest", required=True); p.add_argument("--server-option", action="append", default=[]); p.set_defaults(func=cmd_prepare_instance)
    p = sub.add_parser("start"); p.add_argument("--instance-manifest", required=True); p.add_argument("--timeout", type=int, default=120); p.set_defaults(func=cmd_start)
    p = sub.add_parser("stop"); p.add_argument("--instance-manifest", required=True); p.add_argument("--timeout", type=int, default=60); p.set_defaults(func=cmd_stop)
    p = sub.add_parser("baseline"); add_common(p); p.add_argument("--instance-manifest", required=True); p.set_defaults(func=cmd_baseline)
    p = sub.add_parser("reproduce"); add_common(p); p.add_argument("--instance-manifest", required=True); p.add_argument("--scenario", required=True); p.add_argument("--timeout", type=int); p.set_defaults(func=cmd_reproduce)
    p = sub.add_parser("mtr"); add_common(p); p.add_argument("--source-dir", required=True); p.add_argument("--build-dir"); p.add_argument("--test", action="append", required=True); p.add_argument("--mtr-arg", action="append", default=[]); p.add_argument("--timeout", type=int, default=3600); p.set_defaults(func=cmd_mtr)
    p = sub.add_parser("gdb"); add_common(p); p.add_argument("--mode", choices=["launch", "attach", "core"], required=True); p.add_argument("--instance-manifest"); p.add_argument("--mysqld"); p.add_argument("--pid", type=int); p.add_argument("--core-file"); p.add_argument("--commands"); p.add_argument("--breakpoint", action="append", default=[]); p.add_argument("--timeout", type=int, default=1800); p.set_defaults(func=cmd_gdb)
    p = sub.add_parser("source-diff"); add_common(p); p.add_argument("--before", required=True); p.add_argument("--after", required=True); p.add_argument("--path", action="append"); p.add_argument("--timeout", type=int, default=600); p.set_defaults(func=cmd_source_diff)
    p = sub.add_parser("validate-fix"); add_common(p); p.add_argument("--affected-manifest", required=True); p.add_argument("--fixed-manifest", required=True); p.add_argument("--scenario", required=True); p.add_argument("--iterations", type=int, default=10); p.add_argument("--timeout", type=int, default=600); p.add_argument("--path-coverage-artifact"); p.set_defaults(func=cmd_validate_fix)
    p = sub.add_parser("collect"); add_common(p); p.add_argument("--file", required=True); p.add_argument("--category", choices=["official", "source", "build", "runtime", "mtr", "gdb", "core", "logs", "sql", "patch"], required=True); p.add_argument("--description"); p.set_defaults(func=cmd_collect)
    p = sub.add_parser("confidence"); add_common(p); p.add_argument("--flag", action="append", choices=["reproduced", "fix_validated", "dynamic_evidence", "source_evidence", "official_evidence", "official_fix_test_evidence", "patch_evidence", "mtr_or_fault_injection"], default=[]); p.set_defaults(func=cmd_confidence)
    p = sub.add_parser("report"); add_common(p); p.add_argument("--force", action="store_true"); p.set_defaults(func=cmd_report)
    p = sub.add_parser("report-check"); add_common(p); p.set_defaults(func=cmd_report_check)
    p = sub.add_parser("status"); add_common(p); p.set_defaults(func=cmd_status)
    p = sub.add_parser("skip-phase"); add_common(p); p.add_argument("--phase", choices=PHASES[:-2], required=True); p.add_argument("--reason", required=True); p.set_defaults(func=cmd_skip_phase)
    p = sub.add_parser("cleanup"); add_common(p); p.add_argument("--target", choices=["workspace", "runtime"], required=True); p.set_defaults(func=cmd_cleanup)
    p = sub.add_parser("analyze"); add_common(p); p.add_argument("--description"); p.add_argument("--title"); p.add_argument("--bug-url"); p.set_defaults(func=cmd_analyze)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
