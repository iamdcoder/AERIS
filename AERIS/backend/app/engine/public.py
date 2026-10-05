"""Stable integration facade owned by Person 1.

Person 2 should import these functions, not internal engine modules.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import json
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
_DECISION_CONTEXTS: dict[str, "_DecisionContext"] = {}
_ACTIVE_DECISION_CONTEXT_ID: str | None = None


@dataclass
class _DecisionContext:
    context_id: str
    decision_time: int
    snapshot: dict[str, Any]
    state: Any
    candidate_keys: list[tuple[str, str]] = field(default_factory=list)
    candidate_definitions: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    validation: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    simulation: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    stress: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)


def _engine() -> DigitalTwinSimulator:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = DigitalTwinSimulator(load_world())
    return _ENGINE


def reset_engine() -> None:
    global _ENGINE, _APPLIED_INTERVENTION, _ACTIVE_DECISION_CONTEXT_ID
    with _LOCK:
        _ENGINE = DigitalTwinSimulator(load_world())
        _CANDIDATES.clear()
        _APPLIED_INTERVENTION = None
        _DECISION_CONTEXTS.clear()
        _ACTIVE_DECISION_CONTEXT_ID = None


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


def _make_decision_context(state, candidate_keys: list[tuple[str, str]]) -> _DecisionContext:
    frozen_state = deepcopy(state)
    snapshot = frozen_state.snapshot()
    identity = {
        "snapshot": snapshot,
        "graph_nodes": sorted((node, frozen_state.graph.nodes[node]) for node in frozen_state.graph.nodes),
        "graph_edges": sorted((source, target, data) for source, target, data in frozen_state.graph.edges(data=True)),
        "scenario": frozen_state.scenario,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    context_id = f"DEC-{state.time_min:03d}-{sha256(encoded).hexdigest()[:12]}"
    return _DecisionContext(
        context_id=context_id,
        decision_time=state.time_min,
        snapshot=deepcopy(snapshot),
        state=frozen_state,
        candidate_keys=list(candidate_keys),
    )


def begin_decision_context(
    flight_ids: list[str] | None = None,
    candidates: list[dict] | None = None,
) -> dict[str, Any]:
    """Freeze a deterministic world snapshot for the current candidate decision.

    Evaluation APIs subsequently use private clones of this state, so neither
    later live-world advancement nor route-distance graph enrichment can change
    the evidence or score associated with this decision.
    """
    global _ACTIVE_DECISION_CONTEXT_ID
    with _LOCK:
        state = _engine().state
        selected_flights = set(flight_ids or [key[0] for key in _CANDIDATES])
        keys = [key for key in _CANDIDATES if not selected_flights or key[0] in selected_flights]
        context = _make_decision_context(state, keys)
        supplied = candidates or []
        for candidate in supplied:
            key = _candidate_identity(candidate)
            _require_flight(state, key[0])
            candidate["decision_context_id"] = context.context_id
            context.candidate_definitions[key] = deepcopy(candidate)
            if key not in context.candidate_keys:
                context.candidate_keys.append(key)
        _DECISION_CONTEXTS[context.context_id] = context
        _ACTIVE_DECISION_CONTEXT_ID = context.context_id
        for key in keys:
            _CANDIDATES[key]["decision_context_id"] = context.context_id
            context.candidate_definitions.setdefault(key, deepcopy(_CANDIDATES[key]))
        for key in context.candidate_keys:
            if key in _CANDIDATES:
                _CANDIDATES[key]["decision_context_id"] = context.context_id
        return {
            "decision_time": context.decision_time,
            "snapshot_id": context.context_id,
            "snapshot": deepcopy(context.snapshot),
        }


def get_decision_context(snapshot_id: str | None = None) -> dict[str, Any]:
    """Return a defensive, JSON-safe copy of decision metadata and evidence."""
    with _LOCK:
        context_id = snapshot_id or _ACTIVE_DECISION_CONTEXT_ID
        context = _DECISION_CONTEXTS.get(context_id or "")
        if context is None:
            raise ValueError("No decision context is available")
        candidates = {}
        for key in context.candidate_keys:
            definition = deepcopy(context.candidate_definitions.get(key, {}))
            candidates[key[1]] = {
                "candidate": definition,
                "validation": deepcopy(context.validation.get(key)),
                "simulation": deepcopy(context.simulation.get(key)),
                "stress_report": deepcopy(context.stress.get(key)),
            }
        return {
            "decision_time": context.decision_time,
            "snapshot_id": context.context_id,
            "snapshot": deepcopy(context.snapshot),
            "candidates": candidates,
        }


def _context_for_candidate(
    flight_id: str,
    candidate_id: str,
    snapshot_id: str | None = None,
) -> _DecisionContext:
    global _ACTIVE_DECISION_CONTEXT_ID
    entry = _CANDIDATES.get((flight_id, candidate_id))
    context_id = snapshot_id or (entry.get("decision_context_id") if entry else None)
    context = _DECISION_CONTEXTS.get(context_id or "")
    if context is None:
        active = _DECISION_CONTEXTS.get(_ACTIVE_DECISION_CONTEXT_ID or "")
        if active is not None and active.decision_time == _engine().state.time_min:
            context = active
        else:
            context = _make_decision_context(_engine().state, [(flight_id, candidate_id)])
            _DECISION_CONTEXTS[context.context_id] = context
            _ACTIVE_DECISION_CONTEXT_ID = context.context_id
        if entry is not None:
            entry["decision_context_id"] = context.context_id
        if (flight_id, candidate_id) not in context.candidate_keys:
            context.candidate_keys.append((flight_id, candidate_id))
    return context


def _candidate_for_snapshot(context: _DecisionContext, candidate: dict) -> dict:
    frozen_candidate = deepcopy(candidate)
    key = (candidate["flight_id"], candidate["candidate_id"])
    registered = context.candidate_definitions.get(key) or _CANDIDATES.get(key)
    if registered is not None:
        definition_fields = (
            "candidate_id",
            "flight_id",
            "intervention_type",
            "strategy",
            "route",
            "cruise_altitude_ft",
            "speed_kt",
            "timing_offset_min",
            "hold_min",
        )
        changed = [
            field
            for field in definition_fields
            if field in registered and frozen_candidate.get(field) != registered[field]
        ]
        if changed:
            raise ValueError(
                f"Candidate {key[1]} does not match its registered definition: {', '.join(changed)}"
            )
    original_target = context.state.aircraft.get(key[0])
    if original_target is not None and frozen_candidate.get("route"):
        # Candidate route timing starts at the decision snapshot's actual node;
        # reject stale externally supplied route origins rather than teleporting.
        decision_node = original_target.route[original_target.route_index]
        if frozen_candidate["route"][0] != decision_node:
            raise ValueError(
                f"Candidate {key[1]} starts at {frozen_candidate['route'][0]!r}, "
                f"but decision snapshot starts at {decision_node!r}"
            )
    return frozen_candidate


def generate_alternatives(flight_id: str) -> list[dict]:
    global _ACTIVE_DECISION_CONTEXT_ID
    with _LOCK:
        state = _engine().state
        _require_flight(state, flight_id)
        active_context = _DECISION_CONTEXTS.get(_ACTIVE_DECISION_CONTEXT_ID or "")
        if active_context is not None and active_context.decision_time != state.time_min:
            _ACTIVE_DECISION_CONTEXT_ID = None
        candidates = generate_candidate_routes(state.graph, flight_id)
        for key in [key for key in _CANDIDATES if key[0] == flight_id]:
            del _CANDIDATES[key]
        candidate_keys = []
        for candidate in candidates:
            candidate_flight_id, candidate_id = _candidate_identity(candidate)
            key = (candidate_flight_id, candidate_id)
            candidate_keys.append(key)
            _CANDIDATES[key] = deepcopy(candidate)
        context = _make_decision_context(state, candidate_keys)
        _DECISION_CONTEXTS[context.context_id] = context
        _ACTIVE_DECISION_CONTEXT_ID = context.context_id
        for candidate, key in zip(candidates, candidate_keys):
            candidate["decision_context_id"] = context.context_id
            _CANDIDATES[key]["decision_context_id"] = context.context_id
            context.candidate_definitions[key] = deepcopy(candidate)
        return candidates


def validate_candidate(candidate: dict) -> dict:
    flight_id, candidate_id = _candidate_identity(candidate)
    with _LOCK:
        state = _engine().state
        _require_flight(state, flight_id)
        context = _context_for_candidate(flight_id, candidate_id, candidate.get("decision_context_id"))
        frozen_candidate = _candidate_for_snapshot(context, candidate)
        result = _validate_candidate(deepcopy(context.state), frozen_candidate)
        context.validation[(flight_id, candidate_id)] = deepcopy(result)
        _store_candidate(
            flight_id,
            candidate_id,
            {**frozen_candidate, **result, "decision_context_id": context.context_id},
        )
        return deepcopy(result)


def simulate_candidate(candidate: dict) -> dict:
    flight_id, candidate_id = _candidate_identity(candidate)
    with _LOCK:
        state = _engine().state
        _require_flight(state, flight_id)
        context = _context_for_candidate(flight_id, candidate_id, candidate.get("decision_context_id"))
        frozen_candidate = _candidate_for_snapshot(context, candidate)
        result = _simulate_candidate(deepcopy(context.state), frozen_candidate, horizon_min=20)
        context.simulation[(flight_id, candidate_id)] = deepcopy(result)
        _store_candidate(
            flight_id,
            candidate_id,
            {**frozen_candidate, "simulation": result, "decision_context_id": context.context_id},
        )
        return deepcopy(result)


def stress_test_candidate(candidate: dict) -> dict:
    flight_id, candidate_id = _candidate_identity(candidate)
    with _LOCK:
        state = _engine().state
        _require_flight(state, flight_id)
        context = _context_for_candidate(flight_id, candidate_id, candidate.get("decision_context_id"))
        frozen_candidate = _candidate_for_snapshot(context, candidate)
        results = run_stress_test(deepcopy(context.state), frozen_candidate)
        report = summarize_stress_test(results)
        context.stress[(flight_id, candidate_id)] = deepcopy(report)
        _store_candidate(
            flight_id,
            candidate_id,
            {**frozen_candidate, "stress_report": report, "decision_context_id": context.context_id},
        )
        return deepcopy(report)


def score_candidates(candidates: list[dict]) -> list[dict]:
    with _LOCK:
        prepared: list[tuple[dict, str, str, _DecisionContext, dict, tuple[str, str]]] = []
        for candidate in candidates:
            flight_id, candidate_id = _candidate_identity(candidate)
            _require_flight(_engine().state, flight_id)
            context = _context_for_candidate(
                flight_id,
                candidate_id,
                candidate.get("decision_context_id"),
            )
            frozen_candidate = _candidate_for_snapshot(context, candidate)
            key = (flight_id, candidate_id)
            frozen_candidate["decision_context_id"] = context.context_id
            context.candidate_definitions.setdefault(key, deepcopy(frozen_candidate))
            prepared.append((candidate, flight_id, candidate_id, context, frozen_candidate, key))

        context_ids = {item[3].context_id for item in prepared}
        if len(context_ids) > 1:
            raise ValueError("Candidates from different decision snapshots cannot be ranked together")

        scored = []
        for candidate, flight_id, candidate_id, context, frozen_candidate, key in prepared:
            validation = context.validation.get(key)
            if validation is None:
                validation = _validate_candidate(deepcopy(context.state), frozen_candidate)
                context.validation[key] = deepcopy(validation)
            enriched = {**frozen_candidate, **validation}
            enriched["decision_context"] = {
                "decision_time": context.decision_time,
                "snapshot_id": context.context_id,
                "validation": deepcopy(validation),
            }
            if not validation["feasible"]:
                enriched["decision_score"] = 0.0
                enriched["stress_survival"] = {"passed": 0, "total": 0}
                scored.append(enriched)
                _store_candidate(flight_id, candidate_id, {**enriched, "decision_context_id": context.context_id})
                continue

            simulation = context.simulation.get(key)
            if simulation is None:
                simulation = _simulate_candidate(deepcopy(context.state), frozen_candidate, horizon_min=20)
                context.simulation[key] = deepcopy(simulation)
            stress_report = context.stress.get(key)
            if stress_report is None:
                stress_report = summarize_stress_test(
                    run_stress_test(deepcopy(context.state), frozen_candidate)
                )
                context.stress[key] = deepcopy(stress_report)
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
                "decision_context": {
                    "decision_time": context.decision_time,
                    "snapshot_id": context.context_id,
                    "validation": deepcopy(validation),
                    "simulation": deepcopy(simulation),
                    "stress_report": deepcopy(stress_report),
                },
            })
            scored.append(enriched)
            _store_candidate(flight_id, candidate_id, {**enriched, "decision_context_id": context.context_id})

        original_order = {candidate["candidate_id"]: index for index, candidate in enumerate(candidates)}
        return sorted(
            scored,
            key=lambda item: (
                0 if item.get("feasible") is True else 1,
                -float(item.get("decision_score", 0.0)),
                float(item.get("network_metrics", {}).get("network_ripple_cost", float("inf"))),
                -float(item.get("fuel_reserve_margin_min", float("-inf"))),
                original_order.get(item["candidate_id"], len(original_order)),
                str(item["candidate_id"]),
            ),
        )


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
        target = state.aircraft[flight_id]
        if not target.route or target.route_index >= len(target.route):
            raise ValueError(f"Flight {flight_id} has no current route position")
        live_decision_node = target.route[target.route_index]
        if candidate["route"][0] != live_decision_node:
            raise ValueError(
                f"Candidate {candidate_id} starts at {candidate['route'][0]!r}; "
                f"current decision position is {live_decision_node!r}"
            )
        validation = _validate_candidate(state, candidate)
        if not validation["feasible"]:
            raise ValueError(f"Cannot apply infeasible candidate: {validation['rejection_reasons']}")

        pre_apply_state = deepcopy(state)
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
            "apply_validation": validation,
            "predicted_simulation": stored_candidate.get("simulation"),
            "decision_context_id": stored_candidate.get("decision_context_id"),
            "applied_at_min": state.time_min,
            "pre_apply_state": pre_apply_state,
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
        target = state.aircraft.get(flight_id)
        current_route = (
            target.route[target.route_index :]
            if target is not None and target.route_index < len(target.route)
            else []
        )
        applied_route = _APPLIED_INTERVENTION["candidate"]["route"]
        current_route_is_executed_route = (
            target is not None
            and target.route == applied_route
            and bool(current_route)
            and current_route[0] == target.route[target.route_index]
        )
        if target is not None and target.status == "LANDED":
            validation = None
            route_safe = target.route and target.route[-1] == target.destination
            fuel_safe = target.fuel_remaining_min >= 0
            conflict_safe = True
            restriction_safe = True
            route_valid = bool(route_safe)
        elif target is not None and len(current_route) >= 2:
            executed_candidate = {
                **deepcopy(_APPLIED_INTERVENTION["candidate"]),
                "route": list(current_route),
            }
            validation = _validate_candidate(state, executed_candidate)
            constraints = validation["constraint_results"]
            route_safe = constraints.get("route", {}).get("passed", False)
            route_valid = route_safe
            fuel_safe = constraints.get("fuel", {}).get("feasible", False)
            conflict_safe = constraints.get("conflict", {}).get("passed", False)
            restriction_safe = constraints.get("restriction", {}).get("passed", False)
            all_current_constraints_safe = bool(validation.get("feasible", False))
        else:
            validation = None
            route_safe = fuel_safe = conflict_safe = restriction_safe = route_valid = False
            all_current_constraints_safe = False

        constraints_safe = bool(
            current_route_is_executed_route
            and route_safe
            and route_valid
            and fuel_safe
            and conflict_safe
            and restriction_safe
            and (target is None or target.status == "LANDED" or all_current_constraints_safe)
        )

        # Rebuild a no-intervention world from the exact state immediately
        # before apply, then advance it for the same elapsed verification time.
        baseline_state = deepcopy(_APPLIED_INTERVENTION["pre_apply_state"])
        baseline_state.approved_intervention = None
        baseline_sim = DigitalTwinSimulator(baseline_state)
        elapsed = max(0, state.time_min - int(_APPLIED_INTERVENTION["applied_at_min"]))
        baseline_sim.advance(elapsed)
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
        # no-intervention counterfactual is treated as material degradation.
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
            "verified_at_min": state.time_min,
            "flight_id": flight_id,
            "actual_route": list(current_route),
            "remaining_fuel_min": round(target.fuel_remaining_min, 2) if target is not None else None,
            "route_valid": bool(route_valid),
            "restriction_safe": bool(restriction_safe),
            "conflict_safe": bool(conflict_safe),
            "counterfactual_time_min": baseline_state.time_min,
            "decision_context_id": _APPLIED_INTERVENTION.get("decision_context_id"),
        }
