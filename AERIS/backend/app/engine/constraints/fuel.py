from __future__ import annotations

from ..routes.graph import route_distance_km


MIN_RESERVE_MIN = 12.0


def fuel_feasibility(
    state,
    flight,
    route: list[str],
    speed_kt: float | None = None,
    cruise_altitude_ft: float | None = None,
) -> dict:
    speed = float(flight.speed_kt if speed_kt is None else speed_kt)
    altitude = float(flight.altitude_ft if cruise_altitude_ft is None else cruise_altitude_ft)
    distance_km = route_distance_km(state.graph, route)
    speed_km_min = max(1.0, speed * 1.852 / 60.0)
    low_altitude_limit = getattr(flight, "low_altitude_threshold_ft", None)
    low_altitude_penalty = max(0.0, float(getattr(flight, "low_altitude_fuel_penalty_min", 0.0)))
    alt_penalty = (
        low_altitude_penalty
        if low_altitude_limit is not None and altitude <= float(low_altitude_limit)
        else 0.0
    )
    estimated_flight_min = (distance_km / speed_km_min) * 1.5 + alt_penalty
    reserve_margin = flight.fuel_remaining_min - estimated_flight_min - MIN_RESERVE_MIN
    feasible = reserve_margin >= 0
    return {
        "estimated_route_distance_km": round(distance_km, 2),
        "estimated_flight_time_min": round(estimated_flight_min, 2),
        "fuel_remaining_min": round(flight.fuel_remaining_min, 2),
        "required_reserve_min": MIN_RESERVE_MIN,
        "reserve_margin_min": round(reserve_margin, 2),
        "feasible": feasible,
        "violation_reason": None if feasible else "Insufficient fuel reserve for candidate route",
    }
