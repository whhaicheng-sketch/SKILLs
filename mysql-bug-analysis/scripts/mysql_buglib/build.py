from __future__ import annotations

import json
import shutil
from pathlib import Path

from .command import run_command
from .discovery import inspect_source_tree
from .safety import create_owned_dir, safe_remove_tree


BUILD_STATE_FILE = ".mysql-bug-build.json"


def version_family(version: str) -> str:
    parts = version.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else version


def locate_mysqld(build_dir: Path, install_dir: Path) -> Path | None:
    candidates = [
        install_dir / "bin" / "mysqld",
        build_dir / "runtime_output_directory" / "mysqld",
        build_dir / "bin" / "mysqld",
        build_dir / "sql" / "mysqld",
    ]
    return next((p for p in candidates if p.is_file()), None)


def build_signature(config: dict, source_dir: Path, version: str, role: str) -> dict:
    source = inspect_source_tree(source_dir, managed=False)
    return {
        "version": version,
        "role": role,
        "source_dir": str(source_dir.resolve()),
        "source_commit": source.get("commit"),
        "source_dirty": source.get("dirty"),
        "generator": config["build"].get("generator", "Ninja"),
        "build_type": config["build"].get("default_type", "Debug"),
        "cmake_common_options": list(config["build"].get("cmake_common_options", [])),
        "version_specific_options": list(
            config["build"].get("version_specific_options", {}).get(version_family(version), [])
        ),
    }


def reusable_build(manifest_path: Path, signature: dict) -> bool:
    if not manifest_path.is_file():
        return False
    try:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return existing.get("signature") == signature


def build_mysql(
    config: dict,
    source_dir: Path,
    version: str,
    role: str,
    evidence_dir: Path,
    clean: bool = False,
) -> dict:
    marker = config["safety"]["ownership_marker"]
    build_root = Path(config["paths"]["build_root"])
    install_root = Path(config["paths"]["install_root"])
    build_dir = build_root / f"mysql-{version}-{role}"
    install_dir = install_root / f"mysql-{version}-{role}"
    signature = build_signature(config, source_dir, version, role)

    requested_clean = clean or bool(config["build"].get("clean_build", False))
    if requested_clean:
        if build_dir.exists():
            safe_remove_tree(build_dir, build_root, marker)
        if install_dir.exists():
            safe_remove_tree(install_dir, install_root, marker)

    create_owned_dir(build_dir, marker)
    create_owned_dir(install_dir, marker)
    persistent_manifest = build_dir / BUILD_STATE_FILE

    existing = locate_mysqld(build_dir, install_dir)
    if existing and config["build"].get("reuse_existing_build", True) and not requested_clean:
        if reusable_build(persistent_manifest, signature):
            return _manifest(
                version,
                role,
                source_dir,
                build_dir,
                install_dir,
                existing,
                "reused",
                evidence_dir,
                signature,
            )
        raise RuntimeError(
            f"Existing build does not match the requested source/options: {build_dir}. "
            "Run build with --clean after confirming the directory is Skill-owned."
        )

    generator = config["build"].get("generator", "Ninja")
    cmake = ["cmake", "-S", str(source_dir), "-B", str(build_dir)]
    if generator:
        cmake += ["-G", generator]
    cmake += [f"-DCMAKE_INSTALL_PREFIX={install_dir}"]
    cmake += [str(x) for x in signature["cmake_common_options"]]
    cmake += [str(x) for x in signature["version_specific_options"]]
    run_command(cmake, timeout=1800, log_path=evidence_dir / "cmake.json", check=True)

    jobs = str(config["build"].get("parallel_jobs", 1))
    run_command(
        ["cmake", "--build", str(build_dir), "--parallel", jobs],
        timeout=14400,
        log_path=evidence_dir / "build.json",
        check=True,
    )
    if config["build"].get("install_after_build", True):
        run_command(
            ["cmake", "--install", str(build_dir)],
            timeout=3600,
            log_path=evidence_dir / "install.json",
            check=True,
        )

    mysqld = locate_mysqld(build_dir, install_dir)
    if not mysqld:
        raise FileNotFoundError("Build completed but mysqld was not found")
    persistent_manifest.write_text(
        json.dumps({"signature": signature}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return _manifest(
        version,
        role,
        source_dir,
        build_dir,
        install_dir,
        mysqld,
        "built",
        evidence_dir,
        signature,
    )


def _manifest(
    version: str,
    role: str,
    source_dir: Path,
    build_dir: Path,
    install_dir: Path,
    mysqld: Path,
    status: str,
    evidence_dir: Path,
    signature: dict,
) -> dict:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    info = run_command(
        [str(mysqld), "--version"],
        timeout=30,
        log_path=evidence_dir / "mysqld-version.json",
    )
    file_info = run_command(
        [shutil.which("file") or "file", str(mysqld)],
        timeout=30,
        log_path=evidence_dir / "binary-file.json",
    )
    manifest = {
        "version": version,
        "role": role,
        "source_dir": str(source_dir),
        "build_dir": str(build_dir),
        "install_dir": str(install_dir),
        "mysqld": str(mysqld),
        "status": status,
        "signature": signature,
        "version_output": info.get("stdout", "").strip(),
        "file_output": file_info.get("stdout", "").strip(),
    }
    (evidence_dir / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
