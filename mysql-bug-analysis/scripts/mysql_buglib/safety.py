from __future__ import annotations

import shutil
import socket
from pathlib import Path


def ensure_within(path: Path, root: Path) -> Path:
    resolved_path = path.expanduser().resolve(strict=False)
    resolved_root = root.expanduser().resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise PermissionError(f"Path escapes managed root: {resolved_path} not under {resolved_root}") from exc
    if resolved_path == resolved_root:
        raise PermissionError(f"Refusing to operate on managed root itself: {resolved_root}")
    return resolved_path


def create_owned_dir(path: Path, marker_name: str, *, adopt_existing: bool = False) -> Path:
    if path.exists():
        if not path.is_dir():
            raise NotADirectoryError(path)
        marker = path / marker_name
        if marker.is_file():
            return path
        if any(path.iterdir()) and not adopt_existing:
            raise PermissionError(f"Refusing to adopt non-empty unowned directory: {path}")
    else:
        path.mkdir(parents=True, exist_ok=False)
    marker = path / marker_name
    marker.write_text("owned-by=mysql-bug-analysis\n", encoding="utf-8")
    return path


def require_owned(path: Path, marker_name: str) -> None:
    if not (path / marker_name).is_file():
        raise PermissionError(f"Ownership marker missing: {path / marker_name}")


def safe_remove_tree(path: Path, root: Path, marker_name: str) -> None:
    target = ensure_within(path, root)
    require_owned(target, marker_name)
    shutil.rmtree(target)


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def allocate_port(host: str, start: int, end: int) -> int:
    for port in range(start, end + 1):
        if port_is_available(host, port):
            return port
    raise RuntimeError(f"No available port in {start}-{end}")
