from __future__ import annotations

from shapely.geometry import Point, Polygon


def _route_sector_loads(state, route: list[str]) -> dict[str, int]:
    loads = {sid: 0 for sid in state.sectors}
    for node_id in route:
        for sid, sector in state.sectors.items():
            if node_id in sector.nodes:
                loads[sid] += 1
    return {sid: load for sid, load in loads.items() if load > 0}


def capacity_check(state, route: list[str]) -> dict:
    sector_loads = _route_sector_loads(state, route)
    sector_results = {}
    overloads = []
    max_util = 0.0

    for sid, extra in sector_loads.items():
        sector = state.sectors[sid]
        projected = sector.current_traffic + 1
        utilization = 100.0 * projected / max(1, sector.capacity)
        max_util = max(max_util, utilization)
        passed = projected <= sector.capacity
        sector_results[sid] = {
            "current_traffic": sector.current_traffic,
            "candidate_additional_aircraft": 1,
            "projected_occupancy": projected,
            "capacity": sector.capacity,
            "utilization_pct": round(utilization, 1),
            "passed": passed,
        }
        if not passed:
            overloads.append(sid)

    bom = state.airports.get("BOM")
    airport_result = {"passed": True, "projected_arrival_pressure": 0, "capacity": None}
    if bom and route[-1] == "BOM":
        inbound = sum(1 for f in state.aircraft.values() if f.destination == "BOM" and f.status == "AIRBORNE")
        projected = inbound + 1
        airport_result = {
            "passed": bom.operational_status != "CLOSED",
            "projected_arrival_pressure": projected,
            "capacity": bom.arrival_capacity,
            "operational_status": bom.operational_status,
        }

    return {
        "sectors": sector_results,
        "overloaded_sectors": overloads,
        "max_sector_utilization_pct": round(max_util, 1),
        "airport": airport_result,
        "passed": not overloads and airport_result["passed"],
    }
