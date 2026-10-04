from __future__ import annotations


def resilience_metrics(stress_report: dict, simulation: dict) -> dict:
    survival = float(stress_report.get("survival_pct", 0.0)) / 100.0
    reintervention = 1.0 - survival
    stress_results = stress_report.get("results", [])
    worst_network_delta = max(
        (float(r.get("network_delay_delta_min", 0.0)) for r in stress_results),
        default=0.0,
    )
    regret = max(0.0, worst_network_delta) / 100.0

    return {
        "future_robustness": round(survival, 3),
        "reintervention_probability": round(reintervention, 3),
        "worst_case_network_delay_delta_min": round(worst_network_delta, 2),
        "regret": round(min(1.0, regret), 3),
    }
