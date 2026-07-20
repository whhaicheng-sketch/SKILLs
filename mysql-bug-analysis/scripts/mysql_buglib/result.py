from __future__ import annotations

import json
import sys
from typing import Any


def emit(command: str, success: bool, result: Any = None, *, phase: str | None = None, artifacts: list[str] | None = None, warnings: list[str] | None = None, errors: list[Any] | None = None, next_action: str | None = None) -> int:
    payload = {
        "success": success,
        "command": command,
        "phase": phase,
        "result": result,
        "artifacts": artifacts or [],
        "warnings": warnings or [],
        "errors": errors or [],
        "next_recommended_action": next_action,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if success else 1


def fail(command: str, exc: Exception, *, phase: str | None = None, next_action: str | None = None) -> int:
    return emit(command, False, phase=phase, errors=[{"type": type(exc).__name__, "message": str(exc)}], next_action=next_action)
