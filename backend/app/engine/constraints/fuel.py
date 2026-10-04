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
    speed = float(speed_kt or flight.speed_kt)
    altitude = float(cruise_altitude_ft or flight.altitude_ft)
    distance_km = route_distance_km(state.graph, route)
    speed_km_min = max(1.0, speed * 1.852 / 60.0)
    alt_penalty = 8.0 if altitude <= 26000 else 0.0
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
