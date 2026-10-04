from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..constraints.validator import validate_candidate
from ..simulation.network import simulate_candidate
from .scenarios import build_stress_scenarios, perturb_state


def run_stress_test(state, candidate: dict) -> list[dict[str, Any]]:
    """Run stress testing across all scenario stress profiles for a candidate intervention."""
    results = []
    # Make a deep copy to ensure original state input is never mutated
    state_copy = deepcopy(state)

    for profile in build_stress_scenarios(state_copy):
        scenario_state = perturb_state(deepcopy(state_copy), profile)
        validation = validate_candidate(scenario_state, candidate)

        # Run simulation if route is valid to obtain operational metrics
        route_valid = validation.get("constraint_results", {}).get("route", {}).get("passed", True)
        if route_valid:
            try:
                simulation = simulate_candidate(scenario_state, candidate, horizon_min=20)
            except Exception:
                simulation = {}
        else:
            simulation = {}

        target_delay = float(simulation.get("target_delay_delta_min", 0.0))
        network_delay = float(simulation.get("network_delay_delta_min", 0.0))

        cascade = simulation.get("cascade_indicators", {})
        max_util = float(cascade.get("max_sector_utilization_pct", 0.0)) if isinstance(cascade, dict) else 0.0

        conflict = simulation.get("conflict_impact", {})
        new_conflicts = int(conflict.get("new_conflicts", 0)) if isinstance(conflict, dict) else 0

        constraint_results = validation.get("constraint_results", {})

        capacity_info = constraint_results.get("capacity", {})
        overloaded = list(capacity_info.get("overloaded_sectors", [])) if isinstance(capacity_info, dict) else []

        weather_info = constraint_results.get("weather", {})
        weather_risk = str(weather_info.get("severity", "NONE")) if isinstance(weather_info, dict) else "NONE"

        constraint_failures = {
            "route": not constraint_results.get("route", {}).get("passed", True),
            "fuel": not constraint_results.get("fuel", {}).get("feasible", True),
            "capacity": not constraint_results.get("capacity", {}).get("passed", True),
            "conflict": not constraint_results.get("conflict", {}).get("passed", True),
            "restriction": not constraint_results.get("restriction", {}).get("passed", True),
        }

        # Survival criteria evaluation
        hard_feasible = bool(validation.get("feasible", False))
        no_conflicts = new_conflicts == 0
        target_delay_ok = target_delay <= 25.0
        network_delay_ok = network_delay <= 25.0
        utilization_ok = max_util <= 100.0

        passed = hard_feasible and no_conflicts and target_delay_ok and network_delay_ok and utilization_ok

        failure_reasons = []
        if not constraint_results.get("route", {}).get("passed", True):
            failure_reasons.append("HARD_CONSTRAINT: route")
        if not constraint_results.get("fuel", {}).get("feasible", True):
            failure_reasons.append("HARD_CONSTRAINT: fuel")
        if not constraint_results.get("capacity", {}).get("passed", True):
            failure_reasons.append("HARD_CONSTRAINT: capacity")
        if not constraint_results.get("conflict", {}).get("passed", True):
            failure_reasons.append("HARD_CONSTRAINT: conflict")
        if not constraint_results.get("restriction", {}).get("passed", True):
            failure_reasons.append("HARD_CONSTRAINT: restriction")

        if not target_delay_ok:
            failure_reasons.append("TARGET: delay_delta > 25.0")
        if not network_delay_ok:
            failure_reasons.append("NETWORK: delay_delta > 25.0")
        if not utilization_ok:
            failure_reasons.append("NETWORK: sector utilization > 100%")
        if not no_conflicts:
            failure_reasons.append("CONFLICT: new conflict predicted")

        if not passed and not failure_reasons:
            failure_reasons.append("HARD_CONSTRAINT: validation")

        results.append({
            "scenario_id": str(profile["id"]),
            "scenario_name": str(profile["name"]),
            "passed": passed,
            "target_delay_delta_min": round(target_delay, 3),
            "network_delay_delta_min": round(network_delay, 3),
            "max_sector_utilization_pct": round(max_util, 1),
            "new_conflicts": new_conflicts,
            "weather_risk": weather_risk,
            "capacity_blockers": overloaded,
            "failure_reasons": failure_reasons,
            "constraint_failures": constraint_failures,
        })

    return results
