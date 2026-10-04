from __future__ import annotations

WEIGHTS = {
    "target_flight_benefit": 0.25,
    "network_resilience": 0.25,
    "network_impact": 0.20,
    "fuel_margin": 0.15,
    "future_robustness": 0.15,
}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def score_candidate(network: dict, fuel: dict, resilience: dict, weights: dict | None = None) -> float:
    w = dict(WEIGHTS)
    if weights:
        w.update(weights)

    target = _clamp01(network["target_flight_benefit"] / 12.0)
    network_impact = _clamp01(1.0 - network["network_ripple_cost"] / 15.0)
    fuel_margin = _clamp01(float(fuel.get("reserve_margin_min", 0.0)) / 30.0)
    future = _clamp01(float(resilience.get("future_robustness", 0.0)))
    resilience_component = _clamp01(future * (1.0 - float(resilience.get("reintervention_probability", 0.0))))

    score = (
        w["target_flight_benefit"] * target
        + w["network_resilience"] * resilience_component
        + w["network_impact"] * network_impact
        + w["fuel_margin"] * fuel_margin
        + w["future_robustness"] * future
    )
    return round(score, 3)
