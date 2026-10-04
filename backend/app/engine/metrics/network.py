from __future__ import annotations


def network_impact_metrics(simulation: dict) -> dict:
    network_delta = float(simulation.get("network_delay_delta_min", 0.0))
    affected = int(simulation.get("affected_flights", 0))
    max_util = float(simulation.get("cascade_indicators", {}).get("max_sector_utilization_pct", 0.0))
    target_delta = float(simulation.get("target_delay_delta_min", 0.0))

    return {
        "target_flight_benefit": round(max(0.0, -target_delta), 3),
        "target_delay_delta_min": round(target_delta, 3),
        "network_ripple_cost": round(max(0.0, network_delta) + affected * 0.5, 3),
        "network_delay_delta_min": round(network_delta, 3),
        "affected_flights": affected,
        "max_sector_utilization_pct": round(max_util, 1),
        "new_conflicts": simulation.get("conflict_impact", {}).get("new_conflicts", 0),
    }
