"""Stable integration facade owned by Person 1.

Person 2 should import these functions, not internal engine modules.
"""
from __future__ import annotations

from threading import Lock

from .constraints.validator import validate_candidate as _validate_candidate
from .digital_twin.simulator import DigitalTwinSimulator
from .digital_twin.loaders import load_world
from .metrics.network import network_impact_metrics
from .metrics.resilience import resilience_metrics
from .metrics.score import score_candidate
from .routes.generator import generate_candidate_routes
from .simulation.network import simulate_candidate as _simulate_candidate
from .simulation.transitions import apply_candidate_to_flight
from .stress_test.report import summarize_stress_test
from .stress_test.runner import run_stress_test


_LOCK = Lock()
_ENGINE: DigitalTwinSimulator | None = None


def _engine() -> DigitalTwinSimulator:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = DigitalTwinSimulator(load_world())
    return _ENGINE


def reset_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = DigitalTwinSimulator(load_world())


def advance_simulation(minutes: int = 1) -> dict:
    return _engine().advance(minutes).snapshot()


def get_airspace_state() -> dict:
    return _engine().state.snapshot()


def generate_alternatives(flight_id: str) -> list[dict]:
    state = _engine().state
    return generate_candidate_routes(state.graph, flight_id)


def validate_candidate(candidate: dict) -> dict:
    return _validate_candidate(_engine().state, candidate)


def simulate_candidate(candidate: dict) -> dict:
    return _simulate_candidate(_engine().state, candidate, horizon_min=20)


def stress_test_candidate(candidate: dict) -> dict:
    results = run_stress_test(_engine().state, candidate)
    return summarize_stress_test(results)


def score_candidates(candidates: list[dict]) -> list[dict]:
    state = _engine().state
    scored = []
    for candidate in candidates:
        validation = _validate_candidate(state, candidate)
        enriched = dict(candidate)
        enriched["feasible"] = validation["feasible"]
        enriched["constraint_results"] = validation["constraint_results"]
        enriched["rejection_reasons"] = validation["rejection_reasons"]
        if not validation["feasible"]:
            enriched["decision_score"] = 0.0
            enriched["stress_survival"] = {"passed": 0, "total": 0}
            scored.append(enriched)
            continue

        simulation = _simulate_candidate(state, candidate, horizon_min=20)
        stress_results = run_stress_test(state, candidate)
        stress_report = summarize_stress_test(stress_results)
        network = network_impact_metrics(simulation)
        fuel = validation["constraint_results"]["fuel"]
        resilience = resilience_metrics(stress_report, simulation)

        enriched.update({
            "target_delay_min": round(simulation["target_delay_delta_min"], 2),
            "added_distance_km": round(max(0.0, candidate.get("added_distance_km") or 0.0), 2),
            "fuel_reserve_margin_min": fuel["reserve_margin_min"],
            "affected_flights": simulation["affected_flights"],
            "network_delay_delta_min": simulation["network_delay_delta_min"],
            "max_sector_utilization_pct": simulation["cascade_indicators"]["max_sector_utilization_pct"],
            "stress_survival": {"passed": stress_report["passed"], "total": stress_report["total"]},
            "reintervention_probability": resilience["reintervention_probability"],
            "regret": resilience["regret"],
            "decision_score": score_candidate(network, fuel, resilience),
            "network_metrics": network,
            "resilience_metrics": resilience,
            "simulation": simulation,
        })
        scored.append(enriched)

    return sorted(scored, key=lambda c: c.get("decision_score", 0), reverse=True)


def apply_intervention(candidate_id: str) -> dict:
    engine = _engine()
    state = engine.state
    candidates = generate_alternatives("F102")
    matches = [c for c in candidates if c["candidate_id"] == candidate_id]
    if not matches:
        raise ValueError(f"Unknown candidate: {candidate_id}")
    candidate = matches[0]
    validation = _validate_candidate(state, candidate)
    if not validation["feasible"]:
        raise ValueError(f"Cannot apply infeasible candidate: {validation['rejection_reasons']}")

    apply_candidate_to_flight(state.aircraft[candidate["flight_id"]], candidate)
    state.approved_intervention = candidate_id
    state.event_log.append({"t": state.time_min, "event": "intervention_applied", "candidate_id": candidate_id})
    return {
        "status": "EXECUTING",
        "candidate_id": candidate_id,
        "flight_id": candidate["flight_id"],
    }


def verify_state(candidate_id: str) -> dict:
    engine = _engine()
    state = engine.state
    if state.approved_intervention != candidate_id:
        raise ValueError("Intervention has not been applied")

    # Compare the executed state against a clean state advanced equally long.
    executed = state
    baseline_sim = DigitalTwinSimulator(load_world())
    baseline_sim.advance(executed.time_min)

    executed_total_delay = sum(f.delay_min for f in executed.aircraft.values())
    baseline_total_delay = sum(f.delay_min for f in baseline_sim.state.aircraft.values())
    new_degradation = executed_total_delay > baseline_total_delay + 5.0
    constraints_safe = True
    target = executed.aircraft["F102"]
    if target.fuel_remaining_min <= 0:
        constraints_safe = False

    status = "REASSESSMENT_REQUIRED" if new_degradation or not constraints_safe else "VERIFIED"
    return {
        "status": status,
        "target_delay_delta_min": round(target.delay_min, 2),
        "affected_flights": sum(1 for f in executed.aircraft.values() if f.delay_min > 0.5),
        "network_delay_delta_min": round(executed_total_delay - baseline_total_delay, 2),
        "constraints_safe": constraints_safe,
        "new_degradation": new_degradation,
        "reassessment_required": status == "REASSESSMENT_REQUIRED",
    }
