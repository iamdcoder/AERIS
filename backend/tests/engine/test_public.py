from copy import deepcopy
import json

import pytest

from app.engine import public
from app.engine.digital_twin.loaders import load_world
from app.engine.digital_twin.simulator import DigitalTwinSimulator
from app.models.aircraft import Aircraft


@pytest.fixture(autouse=True)
def fresh_engine():
    public.reset_engine()
    yield
    public.reset_engine()


def _candidate(candidate_id: str = "ALT-A", flight_id: str = "F102") -> dict:
    state = public._engine().state
    candidates = public.generate_alternatives(flight_id)
    candidate = next(item for item in candidates if item["candidate_id"] == candidate_id)
    return deepcopy(candidate)


def _feasible_validation(candidate: dict) -> dict:
    return {
        "candidate_id": candidate["candidate_id"],
        "flight_id": candidate["flight_id"],
        "feasible": True,
        "constraint_results": {
            "fuel": {"feasible": True, "reserve_margin_min": 100.0},
            "conflict": {"passed": True},
            "restriction": {"passed": True},
        },
        "rejection_reasons": [],
        "weather_risk": "NONE",
    }


def test_reset_engine_produces_fresh_deterministic_engine_and_clears_registry():
    public.advance_simulation(2)
    public.generate_alternatives("F102")
    previous_engine = public._ENGINE
    expected = DigitalTwinSimulator(load_world()).state.snapshot()

    public.reset_engine()

    assert public._ENGINE is not previous_engine
    assert public.get_airspace_state() == expected
    assert public._CANDIDATES == {}
    assert public._APPLIED_INTERVENTION is None


def test_generate_alternatives_returns_and_registers_five_candidates():
    candidates = public.generate_alternatives("F102")

    assert len(candidates) == 5
    assert len(public._CANDIDATES) == 5
    assert all((candidate["flight_id"], candidate["candidate_id"]) in public._CANDIDATES for candidate in candidates)
    assert [candidate["candidate_id"] for candidate in candidates] == ["ALT-A", "ALT-B", "ALT-C", "ALT-D", "ALT-E"]


def test_generate_alternatives_rejects_unknown_flight():
    with pytest.raises(ValueError, match="Unknown flight: F999"):
        public.generate_alternatives("F999")


def test_regenerating_candidates_replaces_stale_evaluation_fields():
    candidates = public.generate_alternatives("F102")
    public._CANDIDATES[("F102", "ALT-A")]["decision_score"] = 0.9
    public._CANDIDATES[("F102", "OLD")] = {"flight_id": "F102", "candidate_id": "OLD"}

    regenerated = public.generate_alternatives("F102")

    assert regenerated == candidates
    assert len(public._CANDIDATES) == 5
    assert "decision_score" not in public._CANDIDATES[("F102", "ALT-A")]
    assert ("F102", "OLD") not in public._CANDIDATES


def test_validate_candidate_merges_evaluation_without_mutating_argument(monkeypatch):
    candidate = _candidate()
    original = deepcopy(candidate)
    monkeypatch.setattr(public, "_validate_candidate", lambda state, item: _feasible_validation(item))

    result = public.validate_candidate(candidate)

    assert candidate == original
    assert result["feasible"] is True
    stored = public._CANDIDATES[("F102", "ALT-A")]
    assert stored["route"] == candidate["route"]
    assert stored["constraint_results"]["fuel"]["feasible"] is True
    assert stored["weather_risk"] == "NONE"


def test_validate_candidate_rejects_malformed_candidate():
    with pytest.raises(ValueError, match="missing required field"):
        public.validate_candidate({"candidate_id": "bad"})


def test_simulate_candidate_is_json_serializable_and_stored():
    candidate = _candidate()

    result = public.simulate_candidate(candidate)

    json.dumps(result)
    assert result["candidate_id"] == candidate["candidate_id"]
    assert public._CANDIDATES[("F102", "ALT-A")]["simulation"] == result


def test_stress_test_candidate_returns_and_stores_report(monkeypatch):
    candidate = _candidate()
    monkeypatch.setattr(public, "run_stress_test", lambda state, item: [{"passed": True}])
    monkeypatch.setattr(public, "summarize_stress_test", lambda results: {"passed": 1, "total": 1})

    report = public.stress_test_candidate(candidate)

    assert report == {"passed": 1, "total": 1}
    assert public._CANDIDATES[("F102", "ALT-A")]["stress_report"] == report


def test_score_candidates_enriches_sorts_and_stores_results():
    public.advance_simulation(19)
    candidates = public.generate_alternatives("F102")

    scored = public.score_candidates(candidates)

    assert len(scored) == 5
    scores = [candidate["decision_score"] for candidate in scored]
    assert scores == sorted(scores, reverse=True)
    for candidate in scored:
        stored = public._CANDIDATES[(candidate["flight_id"], candidate["candidate_id"])]
        assert stored == candidate
        assert "constraint_results" in candidate
        assert "simulation" in candidate or candidate["decision_score"] == 0.0


def test_infeasible_candidate_is_stored_with_zero_score(monkeypatch):
    candidate = _candidate()
    monkeypatch.setattr(
        public,
        "_validate_candidate",
        lambda state, item: {
            **_feasible_validation(item),
            "feasible": False,
            "rejection_reasons": ["test rejection"],
        },
    )

    scored = public.score_candidates([candidate])

    assert scored[0]["decision_score"] == 0.0
    assert scored[0]["rejection_reasons"] == ["test rejection"]
    assert scored[0]["stress_survival"] == {"passed": 0, "total": 0}
    assert public._CANDIDATES[("F102", "ALT-A")] == scored[0]


def test_apply_intervention_resolves_synthetic_non_flagship_flight(monkeypatch):
    state = public._engine().state
    synthetic = state.aircraft["F102"].model_copy(deep=True)
    synthetic.id = "F999"
    synthetic.callsign = "F999"
    state.aircraft["F999"] = synthetic
    candidate = public.generate_alternatives("F102")[-1]
    candidate = {**candidate, "flight_id": "F999", "candidate_id": "SYN-ALT"}
    public._CANDIDATES[("F999", "SYN-ALT")] = deepcopy(candidate)
    monkeypatch.setattr(public, "_validate_candidate", lambda current, item: _feasible_validation(item))

    result = public.apply_intervention("SYN-ALT")

    assert result == {"status": "EXECUTING", "candidate_id": "SYN-ALT", "flight_id": "F999"}
    assert state.aircraft["F999"].route == candidate["route"]
    assert state.aircraft["F102"].route != candidate["route"]
    assert state.event_log[-1]["flight_id"] == "F999"
    assert state.approved_intervention == "SYN-ALT"


def test_apply_revalidates_registered_candidate_against_current_state(monkeypatch):
    candidate = _candidate()
    calls = []

    def reject_current(state, item):
        calls.append((state, item))
        return {**_feasible_validation(item), "feasible": False, "rejection_reasons": ["now blocked"]}

    monkeypatch.setattr(public, "_validate_candidate", reject_current)

    with pytest.raises(ValueError, match="now blocked"):
        public.apply_intervention(candidate["candidate_id"])

    assert len(calls) == 1
    assert calls[0][0] is public._engine().state
    assert calls[0][1]["candidate_id"] == candidate["candidate_id"]
    assert public._engine().state.approved_intervention is None


def test_apply_unknown_candidate_raises_value_error():
    with pytest.raises(ValueError, match="Unknown candidate"):
        public.apply_intervention("MISSING")


def test_apply_infeasible_candidate_raises_value_error(monkeypatch):
    candidate = _candidate()
    monkeypatch.setattr(
        public,
        "_validate_candidate",
        lambda state, item: {**_feasible_validation(item), "feasible": False, "rejection_reasons": ["blocked"]},
    )

    with pytest.raises(ValueError, match="blocked"):
        public.apply_intervention(candidate["candidate_id"])


def test_apply_returns_execution_context_and_records_event(monkeypatch):
    candidate = _candidate("ALT-B")
    monkeypatch.setattr(public, "_validate_candidate", lambda state, item: _feasible_validation(item))

    result = public.apply_intervention("ALT-B")

    assert result == {"status": "EXECUTING", "candidate_id": "ALT-B", "flight_id": "F102"}
    event = public._engine().state.event_log[-1]
    assert event == {
        "t": public._engine().state.time_min,
        "event": "intervention_applied",
        "candidate_id": "ALT-B",
        "flight_id": "F102",
    }
    assert public._APPLIED_INTERVENTION["candidate"]["route"] == candidate["route"]


def test_verify_rejects_when_no_intervention_has_been_applied():
    with pytest.raises(ValueError, match="No intervention has been applied"):
        public.verify_state("ALT-A")


def test_verify_rejects_wrong_candidate_id(monkeypatch):
    _candidate("ALT-C")
    monkeypatch.setattr(public, "_validate_candidate", lambda state, item: _feasible_validation(item))
    public.apply_intervention("ALT-C")

    with pytest.raises(ValueError, match="not the currently applied"):
        public.verify_state("ALT-A")


def test_verify_returns_contract_fields_with_integer_affected_count(monkeypatch):
    public.advance_simulation(1)
    candidate = _candidate("ALT-D")
    monkeypatch.setattr(public, "_validate_candidate", lambda state, item: _feasible_validation(item))
    public.apply_intervention("ALT-D")
    public.advance_simulation(2)

    result = public.verify_state("ALT-D")

    assert {
        "status",
        "target_delay_delta_min",
        "affected_flights",
        "network_delay_delta_min",
        "constraints_safe",
        "new_degradation",
        "reassessment_required",
    }.issubset(result)
    assert isinstance(result["affected_flights"], int)
    json.dumps(result)


def test_verification_is_deterministic_for_equivalent_states(monkeypatch):
    def run_once():
        public.reset_engine()
        candidate = _candidate("ALT-E")
        public.advance_simulation(1)
        monkeypatch.setattr(public, "_validate_candidate", lambda state, item: _feasible_validation(item))
        public.apply_intervention("ALT-E")
        public.advance_simulation(3)
        return public.verify_state("ALT-E")

    assert run_once() == run_once()


def test_reset_clears_stale_candidate_and_applied_intervention(monkeypatch):
    candidate = _candidate("ALT-A")
    monkeypatch.setattr(public, "_validate_candidate", lambda state, item: _feasible_validation(item))
    public.apply_intervention("ALT-A")
    assert public._CANDIDATES
    assert public._APPLIED_INTERVENTION is not None

    public.reset_engine()

    assert public._CANDIDATES == {}
    assert public._APPLIED_INTERVENTION is None
    with pytest.raises(ValueError, match="Unknown candidate"):
        public.apply_intervention(candidate["candidate_id"])
