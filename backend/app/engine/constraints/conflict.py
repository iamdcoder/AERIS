from __future__ import annotations

from ..routes.graph import haversine_km, route_distance_km


SEPARATION_NM = 5.0
CONFLICT_TIME_MIN = 1.0
SIM_TIME_SCALE = 1.5


def _node_etas(state, flight, route: list[str], speed_kt: float, start_time: float) -> dict[str, float]:
    etas = {route[0]: start_time}
    elapsed = 0.0
    for u, v in zip(route, route[1:]):
        a, b = state.graph.nodes[u], state.graph.nodes[v]
        distance = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
        speed_km_min = max(1.0, speed_kt * 1.852 / 60.0)
        elapsed += (distance / speed_km_min) * SIM_TIME_SCALE
        etas[v] = start_time + elapsed
    return etas


def conflict_check(state, target_flight_id: str, route: list[str], speed_kt: float) -> dict:
    target = state.aircraft[target_flight_id]
    target_etas = _node_etas(state, target, route, speed_kt, state.time_min)
    baseline_nodes = set(target.original_route or target.route[target.route_index:])
    new_candidate_nodes = set(route) - baseline_nodes
    conflicts = []

    for other in state.aircraft.values():
        if other.id == target_flight_id or other.status != "AIRBORNE":
            continue
        other_route = other.route[other.route_index :]
        if len(other_route) < 2:
            continue
        other_etas = _node_etas(state, other, other_route, other.speed_kt, state.time_min)
        shared = set(target_etas).intersection(other_etas)
        for node in shared:
            # Only treat conflicts introduced by a deviation as hard failures.
            # Existing traffic on the currently filed route is surfaced separately by simulation.
            if node not in new_candidate_nodes:
                continue
            delta = abs(target_etas[node] - other_etas[node])
            if delta <= CONFLICT_TIME_MIN:
                conflicts.append({
                    "aircraft": other.id,
                    "waypoint": node,
                    "predicted_time_min": round((target_etas[node] + other_etas[node]) / 2, 2),
                    "time_separation_min": round(delta, 2),
                    "severity": "HIGH" if delta < 1.5 else "MEDIUM",
                    "estimated_lateral_separation_nm": 0.0,
                })
                break

    return {
        "conflicts": conflicts,
        "passed": not conflicts,
        "required_separation_nm": SEPARATION_NM,
        "violation_reason": None if not conflicts else "Predicted same-waypoint conflict within time threshold",
    }
