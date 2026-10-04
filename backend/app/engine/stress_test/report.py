from __future__ import annotations


def summarize_stress_test(results: list[dict]) -> dict:
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    failures = [
        {
            "scenario_id": r["scenario_id"],
            "scenario_name": r["scenario_name"],
            "reason": "; ".join(
                [
                    "new conflict" if r["new_conflicts"] else "",
                    f"sector utilization {r['max_sector_utilization_pct']:.1f}%"
                    if r["max_sector_utilization_pct"] > 100
                    else "",
                    f"network delay delta {r['network_delay_delta_min']:.1f} min"
                    if r["network_delay_delta_min"] > 25
                    else "",
                ]
            ).strip("; "),
        }
        for r in results
        if not r["passed"]
    ]
    return {
        "passed": passed,
        "total": total,
        "survival_pct": round(100 * passed / total, 1) if total else 0.0,
        "failures": failures,
        "results": results,
    }
