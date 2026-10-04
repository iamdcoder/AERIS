from __future__ import annotations


def cascade_score(simulation: dict) -> float:
    affected = float(simulation.get("affected_flights", 0))
    network_delay = max(0.0, float(simulation.get("network_delay_delta_min", 0.0)))
    overload = max(0.0, float(simulation.get("cascade_indicators", {}).get("max_sector_utilization_pct", 0)) - 90.0)
    return round(affected * 0.5 + network_delay * 0.2 + overload * 0.1, 3)
