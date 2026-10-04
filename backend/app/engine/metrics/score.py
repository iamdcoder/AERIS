from __future__ import annotations

import math
from typing import Any

WEIGHTS = {
    "target_flight_benefit": 0.25,
    "network_resilience": 0.25,
    "network_impact": 0.20,
    "fuel_margin": 0.15,
    "future_robustness": 0.15,
}


def _clamp01(x: float) -> float:
    if not math.isfinite(x):
        return 0.0
    return max(0.0, min(1.0, x))


def score_candidate(
    network: dict[str, Any] | None,
    fuel: dict[str, Any] | None,
    resilience: dict[str, Any] | None,
    weights: dict[str, float] | None = None,
) -> float:
    """Calculate normalized, weighted candidate score bounded in [0.0, 1.0]."""
    if not isinstance(network, dict):
        network = {}
    if not isinstance(fuel, dict):
        fuel = {}
    if not isinstance(resilience, dict):
        resilience = {}

    w = dict(WEIGHTS)
    if weights is not None:
        if not isinstance(weights, dict):
            raise ValueError("weights must be a dictionary")
        for k, v in weights.items():
            if k not in WEIGHTS:
                raise ValueError(f"Invalid weight key: {k}")
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0:
                raise ValueError(f"Invalid weight value for {k}: {v}")
            w[k] = float(v)

    total_w = sum(w.values())
    if not math.isfinite(total_w) or total_w <= 0:
        raise ValueError(f"Total weight must be positive and finite, got {total_w}")

    w_norm = {k: v / total_w for k, v in w.items()}

    try:
        target_benefit = float(network.get("target_flight_benefit", 0.0))
    except (ValueError, TypeError):
        target_benefit = 0.0

    try:
        ripple_cost = float(network.get("network_ripple_cost", 0.0))
    except (ValueError, TypeError):
        ripple_cost = 0.0

    try:
        reserve_margin = float(fuel.get("reserve_margin_min", 0.0))
    except (ValueError, TypeError):
        reserve_margin = 0.0

    try:
        future_robustness = float(resilience.get("future_robustness", 0.0))
    except (ValueError, TypeError):
        future_robustness = 0.0

    try:
        reintervention_prob = float(resilience.get("reintervention_probability", 0.0))
    except (ValueError, TypeError):
        reintervention_prob = 0.0

    target = _clamp01(target_benefit / 12.0)
    network_impact = _clamp01(1.0 - ripple_cost / 15.0)
    fuel_margin = _clamp01(reserve_margin / 30.0)
    future = _clamp01(future_robustness)
    resilience_component = _clamp01(future * (1.0 - reintervention_prob))

    score = (
        w_norm["target_flight_benefit"] * target
        + w_norm["network_resilience"] * resilience_component
        + w_norm["network_impact"] * network_impact
        + w_norm["fuel_margin"] * fuel_margin
        + w_norm["future_robustness"] * future
    )

    score_clamped = _clamp01(score)
    return round(score_clamped, 3)
