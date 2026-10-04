"""Stable integration facade owned by Person 1.

Person 2 should import these functions, not internal engine modules.
"""
from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

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


_LOCK = RLock()
_ENGINE: DigitalTwinSimulator | None = None
_CANDIDATES: dict[tuple[str, str], dict[str, Any]] = {}
_APPLIED_INTERVENTION: dict[str, Any] | None = None


def _engine() -> DigitalTwinSimulator:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = DigitalTwinSimulator(load_world())
    return _ENGINE


def reset_engine() -> None:
    global _ENGINE, _APPLIED_INTERVENTION
    with _LOCK:
        _ENGINE = DigitalTwinSimulator(load_world())
        _CANDIDATES.clear()
        _APPLIED_INTERVENTION = None


def advance_simulation(minutes: int = 1) -> dict:
    with _LOCK:
        return _engine().advance(minutes).snapshot()


def get_airspace_state() -> dict:
    with _LOCK:
        return _engine().state.snapshot()


def _candidate_identity(candidate: dict) -> tuple[str, str]:
    if not isinstance(candidate, dict):
        raise ValueError("Candidate must be a dictionary")
    missing = [key for key in ("flight_id", "candidate_id", "route") if key not in candidate]
    if missing:
        raise ValueError(f"Candidate is missing required field(s): {', '.join(missing)}")
    flight_id = candidate["flight_id"]
    candidate_id = candidate["candidate_id"]
    if not isinstance(flight_id, str) or not flight_id:
        raise ValueError("Candidate flight_id must be a non-empty string")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise ValueError("Candidate candidate_id must be a non-empty string")
    if not isinstance(candidate["route"], list) or not candidate["route"]:
        raise ValueError("Candidate route must be a non-empty list")
    return flight_id, candidate_id


def _require_flight(state, flight_id: str) -> None:
    if flight_id not in state.aircraft:
        raise ValueError(f"Unknown flight: {flight_id}")


def _store_candidate(flight_id: str, candidate_id: str, fields: dict[str, Any]) -> None:
    key = (flight_id, candidate_id)
    entry = dict(_CANDIDATES.get(key, {}))
    entry.update(deepcopy(fields))
    _CANDIDATES[key] = entry


def generate_alternatives(flight_id: str) -> list[dict]:
    with _LOCK:
        state = _engine().state
        _require_flight(state, flight_id)
        candidates = generate_candidate_routes(state.graph, flight_id)
        for key in [key for key in _CANDIDATES if key[0] == flight_id]:
            del _CANDIDATES[key]
        for candidate in candidates:
            candidate_flight_id, candidate_id = _candidate_identity(candidate)
            _CANDIDATES[(candidate_flight_id, candidate_id)] = deepcopy(candidate)
        return candidates


def validate_candidate(candidate: dict) -> dict:
    flight_id, candidate_id = _candidate_identity(candidate)
    with _LOCK:
        state = _engine().state
        _require_flight(state, flight_id)
        result = _validate_candidate(state, candidate)
        _store_candidate(flight_id, candidate_id, {**candidate, **result})
        return result


def simulate_candidate(candidate: dict) -> dict:
    flight_id, candidate_id = _candidate_identity(candidate)
    with _LOCK:
        state = _engine().state
        _require_flight(state, flight_id)
        result = _simulate_candidate(state, candidate, horizon_min=20)
        _store_candidate(flight_id, candidate_id, {**candidate, "simulation": result})
        return result


def stress_test_candidate(candidate: dict) -> dict:
    flight_id, candidate_id = _candidate_identity(candidate)
    with _LOCK:
        state = _engine().state
        _require_flight(state, flight_id)
        results = run_stress_test(state, candidate)
        report = summarize_stress_test(results)
        _store_candidate(flight_id, candidate_id, {**candidate, "stress_report": report})
        return report


def score_candidates(candidates: list[dict]) -> list[dict]:
    with _LOCK:
        state = _engine().state
        scored = []
        for candidate in candidates:
            flight_id, candidate_id = _candidate_identity(candidate)
            _require_flight(state, flight_id)
            validation = _validate_candidate(state, candidate)
            enriched = {**candidate, **validation}
            if not validation["feasible"]:
                enriched["decision_score"] = 0.0
                enriched["stress_survival"] = {"passed": 0, "total": 0}
                scored.append(enriched)
                _store_candidate(flight_id, candidate_id, enriched)
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
                "stress_report": stress_report,
            })
            scored.append(enriched)
            _store_candidate(flight_id, candidate_id, enriched)

        return sorted(scored, key=lambda c: c.get("decision_score", 0), reverse=True)


def apply_intervention(candidate_id: str) -> dict:
    global _APPLIED_INTERVENTION
    with _LOCK:
        state = _engine().state
        matches = [
            (key, value) for key, value in _CANDIDATES.items()
            if key[1] == candidate_id and value.get("candidate_id") == candidate_id
        ]
        if not matches:
            raise ValueError(f"Unknown candidate: {candidate_id}")
        if len(matches) > 1:
            raise ValueError(f"Candidate ID {candidate_id!r} is ambiguous across flights")

        (flight_id, _), stored_candidate = matches[0]
        candidate = deepcopy(stored_candidate)
        _require_flight(state, flight_id)
        validation = _validate_candidate(state, candidate)
        _store_candidate(flight_id, candidate_id, {**candidate, **validation})
        if not validation["feasible"]:
            raise ValueError(f"Cannot apply infeasible candidate: {validation['rejection_reasons']}")

        apply_candidate_to_flight(state.aircraft[flight_id], candidate)
        state.approved_intervention = candidate_id
        state.event_log.append({
            "t": state.time_min,
            "event": "intervention_applied",
            "candidate_id": candidate_id,
            "flight_id": flight_id,
        })
        _APPLIED_INTERVENTION = {
            "candidate_id": candidate_id,
            "flight_id": flight_id,
            "candidate": candidate,
            "validation": validation,
            "predicted_simulation": stored_candidate.get("simulation"),
        }
        return {"status": "EXECUTING", "candidate_id": candidate_id, "flight_id": flight_id}


def verify_state(candidate_id: str) -> dict:
    with _LOCK:
        state = _engine().state
        if _APPLIED_INTERVENTION is None or state.approved_intervention is None:
            raise ValueError("No intervention has been applied")
        if _APPLIED_INTERVENTION["candidate_id"] != candidate_id or state.approved_intervention != candidate_id:
            raise ValueError(f"Candidate {candidate_id!r} is not the currently applied intervention")

        flight_id = _APPLIED_INTERVENTION["flight_id"]
        candidate = deepcopy(_APPLIED_INTERVENTION["candidate"])
        target = state.aircraft.get(flight_id)
        validation = _validate_candidate(state, candidate) if target is not None else None
        route_matches = target is not None and target.route == candidate["route"]
        fuel_safe = (
            validation is not None
            and validation["constraint_results"].get("fuel", {}).get("feasible", False)
        )
        critical_constraints_safe = (
            validation is not None
            and validation["feasible"]
            and validation["constraint_results"].get("conflict", {}).get("passed", False)
            and validation["constraint_results"].get("restriction", {}).get("passed", False)
        )
        constraints_safe = bool(route_matches and fuel_safe and critical_constraints_safe)

        baseline_sim = DigitalTwinSimulator(load_world())
        baseline_sim.advance(state.time_min)
        baseline_state = baseline_sim.state
        actual_total_delay = sum(f.delay_min for f in state.aircraft.values())
        baseline_total_delay = sum(f.delay_min for f in baseline_state.aircraft.values())
        network_delay_delta = actual_total_delay - baseline_total_delay
        baseline_target = baseline_state.aircraft.get(flight_id)
        target_delay_delta = (
            target.delay_min - baseline_target.delay_min
            if target is not None and baseline_target is not None
            else 0.0
        )
        affected_flights = sum(
            1 for other_id, flight in state.aircraft.items()
            if other_id != flight_id
            and other_id in baseline_state.aircraft
            and flight.delay_min - baseline_state.aircraft[other_id].delay_min > 0.5
        )
        # A total-delay increase above five minutes over the clean same-time
        # baseline is treated as material network degradation.
        new_degradation = network_delay_delta > 5.0
        reassessment_required = new_degradation or not constraints_safe
        status = "REASSESSMENT_REQUIRED" if reassessment_required else "VERIFIED"
        return {
            "status": status,
            "target_delay_delta_min": round(target_delay_delta, 2),
            "affected_flights": affected_flights,
            "network_delay_delta_min": round(network_delay_delta, 2),
            "constraints_safe": constraints_safe,
            "new_degradation": new_degradation,
            "reassessment_required": reassessment_required,
        }
