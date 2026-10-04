from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..constraints.conflict import conflict_check
from ..constraints.weather import weather_intersection
from ..routes.graph import route_distance_km
from ..digital_twin.simulator import DigitalTwinSimulator
from ..digital_twin.state import WorldState
from ...models.aircraft import Aircraft
from .transitions import apply_candidate_to_flight


SIM_TIME_SCALE = 1.5
_WEATHER_SEVERITY_FACTOR = {"HIGH": 1.0, "SEVERE": 1.5}
_KM_PER_COORDINATE_DEGREE = 111.0


def _network_snapshot(state: WorldState) -> dict[str, float | int]:
    return {
        "total_delay_min": sum(f.delay_min for f in state.aircraft.values()),
        "airborne": sum(1 for f in state.aircraft.values() if f.status == "AIRBORNE"),
        "degraded": sum(1 for f in state.aircraft.values() if f.status == "DEGRADED"),
    }


def _sector_profile(state: WorldState, route: list[str]) -> dict[str, int]:
    """Count route nodes per sector using the twin's first-matching-sector rule."""
    profile = {sid: 0 for sid in state.sectors}
    for node in route:
        for sid, sector in state.sectors.items():
            if node in sector.nodes:
                profile[sid] += 1
                break
    return {sid: count for sid, count in profile.items() if count}


def _flights_in_sector(state: WorldState, sector_id: str) -> list[Aircraft]:
    """Return sector occupants in flight-ID order, matching twin occupancy rules."""
    flights: list[Aircraft] = []
    for flight in state.aircraft.values():
        if flight.status in {"LANDED", "CANCELLED"}:
            continue
        if not flight.route or flight.route_index >= len(flight.route):
            continue
        current_node = flight.route[flight.route_index]
        for matching_id, sector in state.sectors.items():
            if current_node in sector.nodes:
                if matching_id == sector_id:
                    flights.append(flight)
                break
    return sorted(flights, key=lambda flight: flight.id)


def _sector_utilization(state: WorldState, sector_id: str) -> float:
    sector = state.sectors[sector_id]
    return round(sector.current_traffic / max(1, sector.capacity) * 100.0, 1)


def _advance_network(
    simulator: DigitalTwinSimulator,
    horizon_min: int,
    is_candidate: bool = False,
    candidate_sectors: set[str] | None = None,
    target_flight_id: str | None = None,
) -> dict[str, Any]:
    """Advance the twin minute-by-minute and add deterministic overload delay.

    Each flight receives at most one congestion increment per sector-occupancy
    event (one simulated minute). An overload of n aircraft above capacity adds
    1 + 0.5 * (n - 1) minutes to each airborne occupant; increments never go
    below zero and are added to, rather than substituted for, existing delay.
    """
    state = simulator.state
    target_id = target_flight_id or state.scenario.get("target_flight_id")
    candidate_sectors = candidate_sectors or set()

    peak_utilization = {
        sid: round((sec.current_traffic + getattr(sec, "forecast_traffic", 0)) / max(1, sec.capacity) * 100.0, 1)
        for sid, sec in state.sectors.items()
    }
    peak_overloaded: set[str] = set()
    affected_flight_ids: set[str] = set()
    congestion_delay_by_sector = {sid: 0.0 for sid in state.sectors}

    for sid, sec in state.sectors.items():
        proj = sec.current_traffic + getattr(sec, "forecast_traffic", 0)
        if proj > sec.capacity or (is_candidate and sid in candidate_sectors and proj >= sec.capacity):
            peak_overloaded.add(sid)

    for _ in range(max(0, horizon_min)):
        simulator.tick()
        overloaded: list[tuple[str, int]] = []
        for sid, sector in sorted(state.sectors.items()):
            live_count = len(_flights_in_sector(state, sid))
            proj = live_count + getattr(sector, "forecast_traffic", 0)
            utilization = round(proj / max(1, sector.capacity) * 100.0, 1)
            sector.utilization_pct = utilization
            peak_utilization[sid] = max(peak_utilization.get(sid, 0.0), utilization)

            is_overloaded = proj > sector.capacity
            if is_candidate and sid in candidate_sectors and proj >= sector.capacity:
                is_overloaded = True

            if is_overloaded:
                overload = max(1, proj - sector.capacity + (1 if is_candidate and sid in candidate_sectors else 0))
                overloaded.append((sid, overload))
                peak_overloaded.add(sid)

        applied_flight_ids: set[str] = set()
        for sid, overload in overloaded:
            delay = max(0.5, 1.0 + 0.5 * (overload - 1))
            flights = _flights_in_sector(state, sid)

            for flight in flights:
                if flight.id in applied_flight_ids:
                    continue
                flight.delay_min += delay
                applied_flight_ids.add(flight.id)
                if flight.id != target_id:
                    affected_flight_ids.add(flight.id)
                congestion_delay_by_sector[sid] += delay

    return {
        "peak_sector_utilization_pct": {
            sid: round(peak_utilization[sid], 1) for sid in sorted(peak_utilization)
        },
        "peak_overloaded_sectors": sorted(peak_overloaded),
        "affected_flight_ids": sorted(affected_flight_ids),
        "affected_flights_count": len(affected_flight_ids),
        "congestion_delay_by_sector": {
            sid: round(delay, 2)
            for sid, delay in sorted(congestion_delay_by_sector.items())
        },
    }


def _route_travel_time_min(graph, route: list[str], speed_kt: float) -> float:
    speed_km_min = max(1.0, speed_kt * 1.852 / 60.0)
    return route_distance_km(graph, route) / speed_km_min * SIM_TIME_SCALE


def _weather_delay_min(state: WorldState, route: list[str], speed_kt: float) -> tuple[float, dict[str, Any]]:
    exposure = weather_intersection(state, route)
    severity = exposure["severity"]
    severity_factor = _WEATHER_SEVERITY_FACTOR.get(severity, 0.0)
    if not exposure["intersects"] or severity_factor == 0.0:
        return 0.0, {"severity": severity, "intersection_length": 0.0, "delay_min": 0.0}

    intersection_length = sum(float(item["intersection_length"]) for item in exposure["affected_segments"])
    exposure_distance_km = intersection_length * _KM_PER_COORDINATE_DEGREE
    speed_km_min = max(1.0, speed_kt * 1.852 / 60.0)
    delay_min = exposure_distance_km / speed_km_min * SIM_TIME_SCALE * severity_factor
    return delay_min, {
        "severity": severity,
        "intersection_length": round(intersection_length, 4),
        "delay_min": round(delay_min, 2),
    }


def simulate_candidate(state, candidate: dict, horizon_min: int = 20) -> dict:
    # Create both worlds before advancing either one: neither simulation can
    # inherit mutations, event effects, or congestion delay from the other.
    baseline_sim = DigitalTwinSimulator(deepcopy(state))
    candidate_sim = DigitalTwinSimulator(deepcopy(state))
    baseline_state = baseline_sim.state
    candidate_state = candidate_sim.state
    target_id = candidate["flight_id"]

    cand_sectors: set[str] = set()
    for node in candidate["route"]:
        for sid, sector in candidate_state.sectors.items():
            if node in sector.nodes:
                cand_sectors.add(sid)

    baseline_network = _advance_network(
        baseline_sim,
        horizon_min,
        is_candidate=False,
        target_flight_id=target_id,
    )
    before = _network_snapshot(baseline_state)
    baseline_target_delay = baseline_state.aircraft[target_id].delay_min

    target = candidate_state.aircraft[target_id]
    baseline_route = target.route[target.route_index :]
    baseline_speed = target.speed_kt
    candidate_speed = float(candidate.get("speed_kt", baseline_speed))
    baseline_route_time = _route_travel_time_min(candidate_state.graph, baseline_route, baseline_speed)
    candidate_route_time = _route_travel_time_min(candidate_state.graph, candidate["route"], candidate_speed)
    target.delay_min += candidate_route_time - baseline_route_time
    weather_delay, weather_detail = _weather_delay_min(candidate_state, candidate["route"], candidate_speed)
    target.delay_min += weather_delay
    apply_candidate_to_flight(target, candidate)
    candidate_network = _advance_network(
        candidate_sim,
        horizon_min,
        is_candidate=True,
        candidate_sectors=cand_sectors,
        target_flight_id=target_id,
    )
    after = _network_snapshot(candidate_state)

    baseline_total_delay = round(float(before["total_delay_min"]), 2)
    candidate_total_delay = round(float(after["total_delay_min"]), 2)
    network_delta = round(candidate_total_delay - baseline_total_delay, 2)
    candidate_target_delay = candidate_state.aircraft[target_id].delay_min
    baseline_target_delay = round(baseline_target_delay, 2)
    candidate_target_delay = round(candidate_target_delay, 2)
    target_delta = round(candidate_target_delay - baseline_target_delay, 2)

    affected_ids = sorted(
        flight_id
        for flight_id in candidate_state.aircraft
        if flight_id != target_id
        and candidate_state.aircraft[flight_id].delay_min - baseline_state.aircraft[flight_id].delay_min > 0.01
    )
    if not affected_ids and candidate_network["affected_flight_ids"]:
        affected_ids = sorted(
            fid for fid in candidate_network["affected_flight_ids"] if fid != target_id
        )

    sector_util = candidate_network["peak_sector_utilization_pct"]
    max_sector_utilization = max(
        (sector_util[sid] for sid in cand_sectors),
        default=max(sector_util.values(), default=0.0),
    )

    sector_ripple_detail: dict[str, dict[str, float]] = {}
    baseline_peaks = baseline_network["peak_sector_utilization_pct"]
    candidate_delays = candidate_network["congestion_delay_by_sector"]
    for sid in sorted(set(baseline_peaks) | set(sector_util)):
        if baseline_peaks.get(sid, 0.0) != sector_util.get(sid, 0.0) or candidate_delays.get(sid, 0.0):
            sector_ripple_detail[sid] = {
                "baseline_peak_utilization_pct": round(baseline_peaks.get(sid, 0.0), 1),
                "peak_utilization_pct": round(sector_util.get(sid, 0.0), 1),
                "congestion_delay_min": round(candidate_delays.get(sid, 0.0), 2),
            }

    conflict_result = conflict_check(
        candidate_state,
        target_id,
        candidate["route"],
        float(candidate.get("speed_kt", target.speed_kt)),
    )

    return {
        "candidate_id": candidate["candidate_id"],
        "target_delay_delta_min": target_delta,
        "baseline_target_delay_min": round(baseline_target_delay, 2),
        "candidate_target_delay_min": round(candidate_target_delay, 2),
        "fuel_effect_min": round(
            state.aircraft[candidate["flight_id"]].fuel_remaining_min
            - candidate_state.aircraft[candidate["flight_id"]].fuel_remaining_min,
            2,
        ),
        "affected_flights": len(affected_ids),
        "network_delay_delta_min": network_delta,
        "sector_utilization": sector_util,
        "conflict_impact": {
            "new_conflicts": len(conflict_result["conflicts"]),
            "details": conflict_result["conflicts"][:5],
        },
        "cascade_indicators": {
            "delay_delta": network_delta,
            "affected_flights": len(affected_ids),
            "affected_flight_ids": affected_ids,
            "degraded_flights_after": after["degraded"],
            "max_sector_utilization_pct": round(max_sector_utilization, 1),
            "peak_overloaded_sectors": candidate_network["peak_overloaded_sectors"],
            "sector_ripple_detail": sector_ripple_detail,
            "congestion_affected_flight_ids": candidate_network["affected_flight_ids"],
            "baseline_congestion_affected_flight_ids": baseline_network["affected_flight_ids"],
            "weather_exposure": weather_detail,
        },
        "baseline_total_delay_min": baseline_total_delay,
        "candidate_total_delay_min": candidate_total_delay,
    }
