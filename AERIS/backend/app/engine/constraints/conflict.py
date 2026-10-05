from __future__ import annotations

from ..routes.graph import haversine_km, route_distance_km


SEPARATION_NM = 5.0
CONFLICT_TIME_MIN = 1.0
SIM_TIME_SCALE = 1.5

# 1 NM = 1.852 km
_KM_PER_NM = 1.852


def _node_etas(state, flight, route: list[str], speed_kt: float, start_time: float) -> dict[str, float]:
    if not route:
        return {}
    if getattr(flight, "status", "") == "HOLDING":
        return {route[0]: start_time}
    etas = {route[0]: start_time}
    elapsed = 0.0
    for u, v in zip(route, route[1:]):
        a, b = state.graph.nodes[u], state.graph.nodes[v]
        distance = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
        speed_km_min = max(1.0, speed_kt * 1.852 / 60.0)
        elapsed += (distance / speed_km_min) * SIM_TIME_SCALE
        etas[v] = start_time + elapsed
    return etas


def _interpolate_position(
    state, route: list[str], etas: dict[str, float], t: float
) -> tuple[float, float] | None:
    """Linearly interpolate aircraft lat/lon at time ``t`` along its route."""
    if not route or len(route) < 2:
        return None
    for u, v in zip(route, route[1:]):
        t_u = etas.get(u)
        t_v = etas.get(v)
        if t_u is None or t_v is None:
            continue
        if t_u <= t <= t_v:
            if t_v == t_u:
                frac = 0.0
            else:
                frac = (t - t_u) / (t_v - t_u)
            a = state.graph.nodes[u]
            b = state.graph.nodes[v]
            lat = a["lat"] + (b["lat"] - a["lat"]) * frac
            lon = a["lon"] + (b["lon"] - a["lon"]) * frac
            return lat, lon
    return None


def _estimated_spatial_separation_nm(
    state,
    target_route: list[str],
    target_etas: dict[str, float],
    other_route: list[str],
    other_etas: dict[str, float],
    conflict_time: float,
) -> float:
    """Estimate closest-point spatial separation (NM) at the predicted conflict time."""
    t_pos = _interpolate_position(state, target_route, target_etas, conflict_time)
    o_pos = _interpolate_position(state, other_route, other_etas, conflict_time)
    if t_pos is None or o_pos is None:
        # Fall back to waypoint-node distance if interpolation fails.
        return 0.0
    dist_km = haversine_km(t_pos[0], t_pos[1], o_pos[0], o_pos[1])
    return round(dist_km / _KM_PER_NM, 2)


def conflict_check(state, target_flight_id: str, route: list[str], speed_kt: float) -> dict:
    target = state.aircraft[target_flight_id]
    target_etas = _node_etas(state, target, route, speed_kt, state.time_min)
    baseline_nodes = set(target.original_route or target.route[target.route_index:])
    new_candidate_nodes = set(route) - baseline_nodes
    conflicts = []

    for other in state.aircraft.values():
        if other.id == target_flight_id or other.status not in {"AIRBORNE", "DEGRADED", "HOLDING"}:
            continue
        other_route = other.route[other.route_index:]
        if len(other_route) < 2:
            continue
        other_etas = _node_etas(state, other, other_route, other.speed_kt, state.time_min)

        # Check 1: Shared node proximity
        shared = set(target_etas).intersection(other_etas)
        conflict_found = False
        for node in shared:
            if node not in new_candidate_nodes:
                continue
            delta = abs(target_etas[node] - other_etas[node])
            if delta <= CONFLICT_TIME_MIN:
                conflict_time = (target_etas[node] + other_etas[node]) / 2.0
                spatial_sep = _estimated_spatial_separation_nm(
                    state,
                    route,
                    target_etas,
                    other_route,
                    other_etas,
                    conflict_time,
                )
                node_idx = route.index(node) if node in route else -1
                segment = f"{route[node_idx - 1]}->{node}" if node_idx > 0 else f"->{node}"

                conflicts.append({
                    "aircraft": other.id,
                    "waypoint": node,
                    "segment": segment,
                    "predicted_time_min": round(conflict_time, 2),
                    "time_separation_min": round(delta, 2),
                    "estimated_spatial_separation_nm": spatial_sep,
                    "required_separation_nm": SEPARATION_NM,
                    "severity": "HIGH" if spatial_sep < SEPARATION_NM else "MEDIUM",
                    "estimated_lateral_separation_nm": spatial_sep,
                })
                conflict_found = True
                break

        if conflict_found:
            continue

        # Check 2: Segment spatial-temporal proximity for candidate deviation edges
        for u, v in zip(route, route[1:]):
            if v not in new_candidate_nodes and u not in new_candidate_nodes:
                continue
            t_u = target_etas.get(u)
            t_v = target_etas.get(v)
            if t_u is None or t_v is None:
                continue
            start_t = int(t_u)
            end_t = int(t_v) + 1
            for t_step in range(start_t, end_t):
                t_pos = _interpolate_position(state, route, target_etas, float(t_step))
                o_pos = _interpolate_position(state, other_route, other_etas, float(t_step))
                if t_pos is not None and o_pos is not None:
                    dist_km = haversine_km(t_pos[0], t_pos[1], o_pos[0], o_pos[1])
                    dist_nm = round(dist_km / _KM_PER_NM, 2)
                    if dist_nm < SEPARATION_NM:
                        conflicts.append({
                            "aircraft": other.id,
                            "waypoint": v,
                            "segment": f"{u}->{v}",
                            "predicted_time_min": float(t_step),
                            "time_separation_min": 0.0,
                            "estimated_spatial_separation_nm": dist_nm,
                            "required_separation_nm": SEPARATION_NM,
                            "severity": "HIGH",
                            "estimated_lateral_separation_nm": dist_nm,
                        })
                        conflict_found = True
                        break
            if conflict_found:
                break

    return {
        "conflicts": conflicts,
        "passed": not conflicts,
        "required_separation_nm": SEPARATION_NM,
        "violation_reason": None if not conflicts else "Predicted same-waypoint conflict within time threshold",
    }
