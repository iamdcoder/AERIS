from __future__ import annotations

from typing import Any


def resilience_metrics(stress_report: dict | None, simulation: dict | None = None) -> dict[str, Any]:
    """Derive deterministic resilience metrics from stress testing and simulation reports."""
    if not isinstance(stress_report, dict):
        stress_report = {}

    raw_survival = stress_report.get("survival_pct")
    if raw_survival is None:
        survival_val = 0.0
    else:
        try:
            survival_val = float(raw_survival) / 100.0
        except (ValueError, TypeError):
            survival_val = 0.0

    future_robustness = max(0.0, min(1.0, survival_val))
    reintervention_prob = max(0.0, min(1.0, 1.0 - future_robustness))

    stress_results = stress_report.get("results")
    if not isinstance(stress_results, list):
        stress_results = []

    deltas = []
    for r in stress_results:
        if isinstance(r, dict) and "network_delay_delta_min" in r:
            try:
                deltas.append(float(r["network_delay_delta_min"]))
            except (ValueError, TypeError):
                pass
        elif isinstance(r, (int, float)):
            deltas.append(float(r))

    worst_network_delta = max(deltas) if deltas else 0.0
    regret = max(0.0, worst_network_delta) / 100.0
    regret_clamped = max(0.0, min(1.0, regret))

    return {
        "future_robustness": round(future_robustness, 3),
        "reintervention_probability": round(reintervention_prob, 3),
        "worst_case_network_delay_delta_min": round(worst_network_delta, 2),
        "regret": round(regret_clamped, 3),
    }
