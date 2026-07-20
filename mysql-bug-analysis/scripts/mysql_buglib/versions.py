from __future__ import annotations

import re

def _key(value: str) -> tuple:
    parts = re.findall(r"\d+|[A-Za-z]+", value)
    return tuple((0, int(p)) if p.isdigit() else (1, p.lower()) for p in parts)

def _sort_versions(values: list[str]) -> list[str]:
    return sorted(set(v for v in values if re.match(r"^\d+\.\d+", v)), key=_key)

def resolve_version_roles(*, research: dict, local_versions: list[str], affected: str | None = None, fixed: str | None = None) -> dict:
    mentioned = _sort_versions([str(x) for x in research.get("versions_mentioned", [])])
    fixed_candidates = _sort_versions([str(x) for x in research.get("fixed_version_candidates", [])])
    local = _sort_versions([str(x) for x in local_versions])
    recommended_fixed = fixed or (fixed_candidates[0] if fixed_candidates else None)
    recommended_affected = affected
    if recommended_affected is None:
        candidates = [v for v in mentioned if v != recommended_fixed]
        if recommended_fixed:
            before = [v for v in candidates if _key(v) < _key(recommended_fixed)]
            if before:
                recommended_affected = before[-1]
        if recommended_affected is None and candidates:
            recommended_affected = candidates[0]
    return {
        "reported_versions": mentioned,
        "fixed_candidates": fixed_candidates,
        "local_versions": local,
        "recommended_affected_version": recommended_affected,
        "recommended_fixed_version": recommended_fixed,
    }
