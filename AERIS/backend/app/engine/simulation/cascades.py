from __future__ import annotations


def _as_nonnegative_float(value: object) -> float:
    try:
        parsed = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return max(0.0, parsed)


def cascade_score(simulation: dict) -> float:
    affected = _as_nonnegative_float(simulation.get("affected_flights", 0))
    network_delay = _as_nonnegative_float(simulation.get("network_delay_delta_min", 0.0))
    indicators = simulation.get("cascade_indicators", {})
    if not isinstance(indicators, dict):
        indicators = {}
    overload = max(
        0.0,
        _as_nonnegative_float(indicators.get("max_sector_utilization_pct", 0)) - 90.0,
    )
    return round(affected * 0.5 + network_delay * 0.2 + overload * 0.1, 3)
