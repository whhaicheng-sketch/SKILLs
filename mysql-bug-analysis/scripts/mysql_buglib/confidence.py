from __future__ import annotations

from typing import Any


def evaluate_confidence(evidence: dict[str, Any]) -> dict[str, Any]:
    reproduced = bool(evidence.get("reproduced"))
    fixed = bool(evidence.get("fix_validated"))
    dynamic = bool(evidence.get("dynamic_evidence"))
    source = bool(evidence.get("source_evidence"))
    official = bool(evidence.get("official_evidence"))
    forced = bool(evidence.get("mtr_or_fault_injection"))
    patch = bool(evidence.get("patch_evidence"))

    if reproduced and fixed and dynamic and source:
        level = "L1"
        reason = "受影响版本复现、修复版本验证、动态证据和源码证据形成闭环。"
    elif (reproduced or forced) and source and (dynamic or patch):
        level = "L2"
        reason = "通过真实复现、MTR、插桩或故障注入获得动态证据，并与源码或补丁一致。"
    elif official and source and patch:
        level = "L3"
        reason = "官方资料、修复补丁与源码调用链形成闭环，但未完成本地自然复现。"
    elif source:
        level = "L4"
        reason = "结论主要来自静态源码分析，缺少充分动态或修复验证证据。"
    else:
        level = "L5"
        reason = "证据不足，仅能提出待验证假设。"
    return {"level": level, "reason": reason}
