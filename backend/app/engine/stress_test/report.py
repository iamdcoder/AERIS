from __future__ import annotations

from typing import Any


def _format_human_reason(failure_reasons: list[str], result: dict) -> str:
    parts = []
    for r in failure_reasons:
        if r.startswith("HARD_CONSTRAINT: "):
            constraint_type = r.split(": ")[1]
            parts.append(f"{constraint_type.capitalize()} hard constraint failed")
        elif r == "TARGET: delay_delta > 25.0":
            target_delay = float(result.get("target_delay_delta_min", 0.0))
            parts.append(f"target delay delta {target_delay:.1f} min")
        elif r == "NETWORK: delay_delta > 25.0":
            net_delay = float(result.get("network_delay_delta_min", 0.0))
            parts.append(f"network delay delta {net_delay:.1f} min")
        elif r == "NETWORK: sector utilization > 100%":
            util = float(result.get("max_sector_utilization_pct", 0.0))
            parts.append(f"sector utilization {util:.1f}%")
        elif r == "CONFLICT: new conflict predicted":
            parts.append("new conflict predicted")
        else:
            parts.append(r)

    if not parts:
        return "Stress scenario failed operational criteria"
    return "; ".join(parts)


def summarize_stress_test(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize stress test scenario results into a top-level report."""
    if not isinstance(results, list):
        results = []

    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)
    survival_pct = round(100.0 * passed / total, 1) if total > 0 else 0.0

    failures = []
    for r in results:
        if not r.get("passed", False):
            reasons = list(r.get("failure_reasons", []))
            failures.append({
                "scenario_id": r.get("scenario_id", ""),
                "scenario_name": r.get("scenario_name", ""),
                "reason": _format_human_reason(reasons, r),
                "failure_reasons": reasons,
            })

    return {
        "passed": passed,
        "total": total,
        "survival_pct": survival_pct,
        "failures": failures,
        "results": results,
    }
