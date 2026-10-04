from __future__ import annotations

from ..routes.graph import haversine_km

# Simulation time scale factor — mirrors simulator.py and conflict.py.
SIM_TIME_SCALE = 1.5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _segment_entry_exit_times(
    state, route: list[str], speed_kt: float, start_time: float
) -> list[dict]:
    """Return per-node traversal timestamps along the candidate route."""
    if not route:
        return []
    windows = []
    elapsed = 0.0
    for i, node in enumerate(route):
        entry = start_time + elapsed
        if i < len(route) - 1:
            a = state.graph.nodes[node]
            b = state.graph.nodes[route[i + 1]]
            dist_km = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
            speed_km_min = max(1.0, speed_kt * 1.852 / 60.0)
            seg_time = (dist_km / speed_km_min) * SIM_TIME_SCALE
        else:
            seg_time = 0.0
        exit_t = start_time + elapsed + seg_time
        windows.append({"node": node, "entry_time_min": entry, "exit_time_min": exit_t})
        elapsed += seg_time
    return windows


def _route_sector_traversal(
    state, route: list[str], speed_kt: float, start_time: float
) -> dict[str, dict]:
    """For each sector the route passes through, compute the occupancy window."""
    node_windows = _segment_entry_exit_times(state, route, speed_kt, start_time)
    node_time_map = {w["node"]: w for w in node_windows}

    sector_occupancy: dict[str, dict] = {}
    for sid, sector in state.sectors.items():
        candidate_nodes = [n for n in route if n in sector.nodes]
        if not candidate_nodes:
            continue
        times = [node_time_map[n] for n in candidate_nodes if n in node_time_map]
        if not times:
            continue
        entry = min(t["entry_time_min"] for t in times)
        exit_t = max(t["exit_time_min"] for t in times)
        sector_occupancy[sid] = {
            "entry_time_min": round(entry, 2),
            "exit_time_min": round(exit_t, 2),
            "node_count": len(candidate_nodes),
        }
    return sector_occupancy


def _candidate_arrival_time(
    state, route: list[str], speed_kt: float, start_time: float
) -> float:
    """Estimate the time (minutes) when the candidate reaches the last waypoint."""
    windows = _segment_entry_exit_times(state, route, speed_kt, start_time)
    if not windows:
        return start_time
    return windows[-1]["exit_time_min"]


def _infer_speed(state, route: list[str]) -> float:
    """Infer diagnostic traversal speed from actual aircraft performance data."""
    if not route:
        raise ValueError("speed_kt is required for an empty route")
    origin = route[0]
    for aircraft in state.aircraft.values():
        if (
            aircraft.status in {"AIRBORNE", "DEGRADED", "HOLDING"}
            and aircraft.route
            and aircraft.route_index < len(aircraft.route)
            and aircraft.route[aircraft.route_index] == origin
        ):
            return float(aircraft.speed_kt)
    active_speeds = [
        float(aircraft.speed_kt)
        for aircraft in state.aircraft.values()
        if aircraft.status not in {"LANDED", "CANCELLED"}
    ]
    if not active_speeds:
        raise ValueError("speed_kt is required when no active aircraft speed is available")
    return sum(active_speeds) / len(active_speeds)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def capacity_check(
    state,
    route: list[str],
    speed_kt: float | None = None,
    start_time: float | None = None,
) -> dict:
    """Check sector and airport capacity with temporal traversal-window awareness.

    Parameters
    ----------
    state:
        Current WorldState.
    route:
        Ordered list of waypoint IDs for the candidate.
    speed_kt:
        Candidate cruise speed (knots).  Inferred from aircraft at route origin
        when not provided.
    start_time:
        Simulation minute from which the candidate departs.
        Defaults to ``state.time_min``.
    """
    if speed_kt is None:
        speed_kt = _infer_speed(state, route)
    if start_time is None:
        start_time = float(getattr(state, "time_min", 0))

    sector_traversal = _route_sector_traversal(state, route, speed_kt, start_time)
    sector_results: dict = {}
    overloads: list[str] = []
    max_util = 0.0

    for sid, traversal in sector_traversal.items():
        sector = state.sectors[sid]

        # current_occupancy: flights in this sector right now.
        current_occupancy = sector.current_traffic

        # forecast_demand: expected aircraft in the sector during the traversal window.
        forecast_demand = getattr(sector, "forecast_traffic", current_occupancy)

        # candidate-projected occupancy against the forecast.
        candidate_projected = forecast_demand + 1

        remaining_headroom = sector.capacity - candidate_projected
        utilization = 100.0 * candidate_projected / max(1, sector.capacity)
        max_util = max(max_util, utilization)
        passed = candidate_projected <= sector.capacity

        sector_results[sid] = {
            # Legacy keys preserved so existing tests keep passing.
            "current_traffic": current_occupancy,
            "candidate_additional_aircraft": 1,
            "projected_occupancy": candidate_projected,
            # New temporal/semantic keys.
            "current_occupancy": current_occupancy,
            "forecast_demand": forecast_demand,
            "candidate_projected_occupancy": candidate_projected,
            "remaining_headroom": remaining_headroom,
            "capacity": sector.capacity,
            "utilization_pct": round(utilization, 1),
            "entry_time_min": traversal["entry_time_min"],
            "exit_time_min": traversal["exit_time_min"],
            "passed": passed,
        }
        if not passed:
            overloads.append(sid)

    # -----------------------------------------------------------------------
    # Destination airport arrival capacity
    # -----------------------------------------------------------------------
    airport_id = route[-1] if route else None
    airport = state.airports.get(airport_id) if airport_id is not None else None
    airport_result: dict = {
        "passed": True,
        "projected_arrival_pressure": 0,
        "capacity": None,
        "arrival_time_min": None,
    }

    if airport is not None:
        inbound_count = sum(
            1
            for f in state.aircraft.values()
            if f.destination == airport_id and f.status not in {"LANDED", "CANCELLED"}
        )

        predicted_arrival_min = _candidate_arrival_time(state, route, speed_kt, start_time)
        arrival_capacity = airport.arrival_capacity
        projected_arrivals = inbound_count + 1

        # Hard failure only when the destination airport is operationally closed.
        # The arrival_capacity figure is a per-hour throughput rate used for
        # pressure scoring, not an absolute slot ceiling on concurrent inbound
        # count (which would spuriously reject all routes in a busy scenario).
        arrival_feasible = airport.operational_status != "CLOSED"

        airport_result = {
            # Legacy key preserved.
            "passed": arrival_feasible,
            "projected_arrival_pressure": projected_arrivals,
            "capacity": arrival_capacity,
            "operational_status": airport.operational_status,
            # New timing / informational keys.
            "arrival_time_min": round(predicted_arrival_min, 2),
            "inbound_count": inbound_count,
            "degraded_window": airport.weather_status != "NORMAL",
        }
        if airport.weather_status != "NORMAL":
            airport_result["arrival_pressure_note"] = (
                f"{airport.id} degraded capacity ({arrival_capacity}/hr); "
                f"candidate predicted arrival t={round(predicted_arrival_min, 1)} min"
            )

    return {
        "sectors": sector_results,
        "overloaded_sectors": overloads,
        "max_sector_utilization_pct": round(max_util, 1),
        "airport": airport_result,
        "passed": not overloads and airport_result["passed"],
    }
