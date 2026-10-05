from __future__ import annotations

from ..routes.graph import route_is_valid
from .capacity import capacity_check
from .conflict import conflict_check
from .fuel import fuel_feasibility
from .performance import performance_check
from .restriction import restriction_check
from .weather import weather_intersection


def validate_candidate(state, candidate: dict) -> dict:
    flight_id = candidate["flight_id"]
    flight = state.aircraft[flight_id]
    route = candidate["route"]
    altitude = float(candidate.get("cruise_altitude_ft", flight.altitude_ft))
    speed = float(candidate.get("speed_kt", flight.speed_kt))

    valid, route_error = route_is_valid(state.graph, route)
    results = {
        "route": {"passed": valid, "error": route_error},
        "weather": weather_intersection(state, route) if valid else {"passed": False},
        "fuel": fuel_feasibility(state, flight, route, speed, altitude) if valid else {"feasible": False},
        "capacity": capacity_check(state, route, speed_kt=speed) if valid else {"passed": False},
        "conflict": conflict_check(state, flight_id, route, speed) if valid else {"passed": False},
        "restriction": restriction_check(state, route, altitude) if valid else {"passed": False},
        "performance": performance_check(state, flight, altitude, speed) if valid else {"passed": False},
    }

    hard_failures = []
    if not results["route"]["passed"]:
        hard_failures.append(route_error or "Invalid route")
    if not results["fuel"].get("feasible", False):
        hard_failures.append(results["fuel"].get("violation_reason", "Fuel constraint failed"))
    if not results["capacity"].get("passed", False):
        hard_failures.extend(
            [f"Sector {sid} exceeds capacity" for sid in results["capacity"].get("overloaded_sectors", [])]
        )
        if not results["capacity"].get("airport", {}).get("passed", True):
            hard_failures.append("Destination airport is operationally closed")
    if not results["conflict"].get("passed", False):
        hard_failures.append(results["conflict"].get("violation_reason", "Conflict constraint failed"))
    if not results["restriction"].get("passed", False):
        hard_failures.append(results["restriction"].get("violation_reason", "Restriction violation"))
    if not results["performance"].get("passed", True):
        hard_failures.append(results["performance"].get("violation_reason", "Performance constraint failed"))

    # Weather is deliberately a risk signal rather than an automatic hard reject in this scenario.
    passed = len(hard_failures) == 0
    return {
        "candidate_id": candidate["candidate_id"],
        "flight_id": flight_id,
        "feasible": passed,
        "constraint_results": results,
        "rejection_reasons": hard_failures,
        "weather_risk": results["weather"].get("severity", "NONE"),
    }
