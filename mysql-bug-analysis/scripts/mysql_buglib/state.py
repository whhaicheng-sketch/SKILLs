from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASES = [
    "DISCOVER", "RESEARCH", "VERSION_RESOLUTION", "PREPARE", "BASELINE",
    "REPRODUCE", "DEBUG", "SOURCE_ANALYSIS", "FIX_VALIDATION",
    "CONCLUSION", "REPORT", "COMPLETE",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskState:
    path: Path
    data: dict[str, Any]

    @classmethod
    def create(cls, bug_id: str, path: Path) -> "TaskState":
        path.parent.mkdir(parents=True, exist_ok=True)
        state = cls(path=path, data={
            "bug_id": str(bug_id),
            "phase": "DISCOVER",
            "completed_phases": [],
            "skipped_phases": [],
            "reproduced": False,
            "fix_validated": False,
            "confidence_level": "L5",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "warnings": [],
            "errors": [],
        })
        state.save()
        return state

    @classmethod
    def load(cls, path: Path) -> "TaskState":
        return cls(path=path, data=json.loads(path.read_text(encoding="utf-8")))

    def save(self) -> None:
        self.data["updated_at"] = utc_now()
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def update(self, **values: Any) -> None:
        self.data.update(values)
        self.save()

    def complete_phase(self, phase: str) -> None:
        if phase not in PHASES:
            raise ValueError(f"Unknown phase: {phase}")
        if phase in self.data.setdefault("completed_phases", []):
            return
        if self.data.get("phase") != phase:
            raise ValueError(f"Cannot complete {phase}; current phase is {self.data.get('phase')}")
        completed = self.data["completed_phases"]
        if phase not in completed:
            completed.append(phase)
        index = PHASES.index(phase)
        self.data["phase"] = PHASES[min(index + 1, len(PHASES) - 1)]
        self.save()

    def skip_phase(self, phase: str, reason: str) -> None:
        if not reason.strip():
            raise ValueError("A non-empty skip reason is required")
        if self.data.get("phase") != phase:
            raise ValueError(f"Cannot skip {phase}; current phase is {self.data.get('phase')}")
        self.data.setdefault("skipped_phases", []).append({
            "phase": phase, "reason": reason.strip(), "at": utc_now(),
        })
        index = PHASES.index(phase)
        self.data["phase"] = PHASES[min(index + 1, len(PHASES) - 1)]
        self.save()
