from __future__ import annotations

from copy import deepcopy

from ..constraints.weather import weather_intersection
from ..simulation.network import simulate_candidate, _sector_profile
from .scenarios import build_stress_scenarios, perturb_state


def _projected_capacity_ok(state, candidate: dict) -> tuple[bool, list[str]]:
    touched = _sector_profile(state, candidate["route"])
    blockers = []
    for sid, dwell_nodes in touched.items():
        sector = state.sectors[sid]
        pressure = max(sector.current_traffic, sector.forecast_traffic)
        # One candidate aircraft plus a small dwell-time penalty in sectors where the route
        # occupies multiple waypoints.
        candidate_load = 1.0 + max(0, dwell_nodes - 2) * 0.5
        if pressure + candidate_load > sector.capacity:
            blockers.append(sid)
    return not blockers, blockers


def run_stress_test(state, candidate: dict) -> list[dict]:
    results = []
    for profile in build_stress_scenarios(state):
        scenario_state = perturb_state(deepcopy(state), profile)
        weather = weather_intersection(scenario_state, candidate["route"])
        capacity_ok, overloaded = _projected_capacity_ok(scenario_state, candidate)
        simulation = simulate_candidate(scenario_state, candidate, horizon_min=20)

        weather_sensitive = weather["intersects"] and weather["severity"] in {"HIGH", "SEVERE"}
        expanded_weather = "weather_expand_factor" in profile
        passed = (
            not (weather_sensitive and expanded_weather)
            and capacity_ok
            and simulation["conflict_impact"]["new_conflicts"] == 0
            and simulation["target_delay_delta_min"] <= 25.0
        )
        results.append({
            "scenario_id": profile["id"],
            "scenario_name": profile["name"],
            "passed": passed,
            "target_delay_delta_min": simulation["target_delay_delta_min"],
            "network_delay_delta_min": simulation["network_delay_delta_min"],
            "max_sector_utilization_pct": simulation["cascade_indicators"]["max_sector_utilization_pct"],
            "new_conflicts": simulation["conflict_impact"]["new_conflicts"],
            "weather_risk": weather["severity"],
            "capacity_blockers": overloaded,
        })
    return results
