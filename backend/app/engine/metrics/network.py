from __future__ import annotations

from typing import Any


def network_impact_metrics(simulation: dict | None) -> dict[str, Any]:
    """Derive deterministic network impact metrics from a simulation result dictionary."""
    if not isinstance(simulation, dict):
        simulation = {}

    try:
        target_delta = float(simulation.get("target_delay_delta_min") or 0.0)
    except (ValueError, TypeError):
        target_delta = 0.0

    try:
        network_delta = float(simulation.get("network_delay_delta_min") or 0.0)
    except (ValueError, TypeError):
        network_delta = 0.0

    try:
        affected = int(simulation.get("affected_flights") or 0)
    except (ValueError, TypeError):
        affected = 0

    cascade = simulation.get("cascade_indicators")
    if not isinstance(cascade, dict):
        cascade = {}
    try:
        max_util = float(cascade.get("max_sector_utilization_pct") or 0.0)
    except (ValueError, TypeError):
        max_util = 0.0

    conflict = simulation.get("conflict_impact")
    if not isinstance(conflict, dict):
        conflict = {}
    try:
        new_conflicts = int(conflict.get("new_conflicts") or 0)
    except (ValueError, TypeError):
        new_conflicts = 0

    target_benefit = max(0.0, -target_delta)
    ripple_cost = max(0.0, network_delta) + affected * 0.5

    return {
        "target_flight_benefit": round(target_benefit, 3),
        "target_delay_delta_min": round(target_delta, 3),
        "network_ripple_cost": round(max(0.0, ripple_cost), 3),
        "network_delay_delta_min": round(network_delta, 3),
        "affected_flights": affected,
        "max_sector_utilization_pct": round(max_util, 1),
        "new_conflicts": new_conflicts,
    }
