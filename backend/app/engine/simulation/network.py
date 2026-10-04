from __future__ import annotations

from copy import deepcopy

from ..constraints.conflict import conflict_check
from ..constraints.weather import weather_intersection
from ..routes.graph import route_distance_km
from ..digital_twin.simulator import DigitalTwinSimulator
from .transitions import apply_candidate_to_flight


def _network_snapshot(state) -> dict:
    return {
        "total_delay_min": round(sum(f.delay_min for f in state.aircraft.values()), 2),
        "airborne": sum(1 for f in state.aircraft.values() if f.status == "AIRBORNE"),
        "degraded": sum(1 for f in state.aircraft.values() if f.status == "DEGRADED"),
        "max_sector_utilization_pct": round(
            max((s.utilization_pct for s in state.sectors.values()), default=0.0), 1
        ),
    }


def _sector_profile(state, route: list[str]) -> dict[str, int]:
    profile = {sid: 0 for sid in state.sectors}
    for node in route:
        for sid, sector in state.sectors.items():
            if node in sector.nodes:
                profile[sid] += 1
                break
    return {sid: count for sid, count in profile.items() if count}


def _ripple_detail(state, target, candidate_route: list[str]) -> tuple[float, dict]:
    baseline = _sector_profile(state, target.original_route or target.route)
    candidate = _sector_profile(state, candidate_route)
    delta = {sid: candidate.get(sid, 0) - baseline.get(sid, 0) for sid in state.sectors}

    ripple = 0.0
    detail: dict = {}
    for sid, d in delta.items():
        if d == 0:
            continue
        sector = state.sectors[sid]
        pressure = max(sector.forecast_traffic, sector.current_traffic) / max(1, sector.capacity)
        if d > 0:
            contribution = d * pressure * 2.5
            ripple += contribution
            detail[sid] = {"delta_nodes": d, "pressure": round(pressure, 2), "ripple_min": round(contribution, 2)}
        else:
            contribution = d * pressure * 4.0
            ripple += contribution
            detail[sid] = {"delta_nodes": d, "pressure": round(pressure, 2), "relief_min": round(contribution, 2)}

    wx = weather_intersection(state, candidate_route)
    if wx["intersects"] and wx["severity"] in {"HIGH", "SEVERE"}:
        ripple += 5.0
        detail["WEATHER"] = {"severity": wx["severity"], "penalty_min": 5.0}

    return ripple, detail


def _apply_background_ripple(state, target_id: str, detail: dict, ripple: float) -> int:
    impact_sectors = [sid for sid in detail if sid != "WEATHER"]
    if "WEATHER" in detail:
        impact_sectors.extend(["S3", "S5"])
    impact_nodes = set()
    for sid in impact_sectors:
        if sid in state.sectors:
            impact_nodes.update(state.sectors[sid].nodes)

    affected = []
    for flight in sorted(state.aircraft.values(), key=lambda f: f.id):
        if flight.id == target_id or flight.status != "AIRBORNE":
            continue
        if impact_nodes.intersection(flight.route):
            affected.append(flight)

    count = min(len(affected), 4)
    if count == 0 or ripple == 0:
        return 0
    per_flight = max(0.5, min(1.5, abs(ripple) / count))
    for flight in affected[:count]:
        if ripple > 0:
            flight.delay_min += per_flight
        else:
            flight.delay_min = max(0.0, flight.delay_min - per_flight)
    return count


def simulate_candidate(state, candidate: dict, horizon_min: int = 20) -> dict:
    baseline_state = deepcopy(state)
    baseline_sim = DigitalTwinSimulator(baseline_state)
    baseline_sim.advance(horizon_min)
    before = _network_snapshot(baseline_state)
    baseline_target_delay = baseline_state.aircraft[candidate["flight_id"]].delay_min

    sim_state = deepcopy(state)
    sim = DigitalTwinSimulator(sim_state)
    target = sim_state.aircraft[candidate["flight_id"]]
    original_distance = route_distance_km(state.graph, target.route[target.route_index :])
    candidate_distance = route_distance_km(state.graph, candidate["route"])
    extra_distance = max(0.0, candidate_distance - original_distance)
    speed_km_min = max(1.0, target.speed_kt * 1.852 / 60.0)
    target.delay_min += extra_distance / speed_km_min * 1.5
    apply_candidate_to_flight(target, candidate)

    ripple, ripple_detail = _ripple_detail(state, target, candidate["route"])
    affected = _apply_background_ripple(sim_state, target.id, ripple_detail, ripple)
    sim.advance(horizon_min)
    after = _network_snapshot(sim_state)

    target_delta = sim_state.aircraft[candidate["flight_id"]].delay_min - baseline_target_delay
    network_delta = after["total_delay_min"] - before["total_delay_min"]
    conflict_result = conflict_check(
        sim_state,
        candidate["flight_id"],
        candidate["route"],
        float(candidate.get("speed_kt", target.speed_kt)),
    )
    sector_util = {sid: round(s.utilization_pct, 1) for sid, s in sim_state.sectors.items()}

    return {
        "candidate_id": candidate["candidate_id"],
        "target_delay_delta_min": round(target_delta, 2),
        "fuel_effect_min": round(
            state.aircraft[candidate["flight_id"]].fuel_remaining_min
            - sim_state.aircraft[candidate["flight_id"]].fuel_remaining_min,
            2,
        ),
        "affected_flights": affected,
        "network_delay_delta_min": round(network_delta, 2),
        "sector_utilization": sector_util,
        "conflict_impact": {
            "new_conflicts": len(conflict_result["conflicts"]),
            "details": conflict_result["conflicts"][:5],
        },
        "cascade_indicators": {
            "delay_delta": round(network_delta, 2),
            "affected_flights": affected,
            "degraded_flights_after": after["degraded"],
            "max_sector_utilization_pct": after["max_sector_utilization_pct"],
            "sector_ripple_detail": ripple_detail,
        },
        "baseline_total_delay_min": before["total_delay_min"],
        "candidate_total_delay_min": after["total_delay_min"],
    }
