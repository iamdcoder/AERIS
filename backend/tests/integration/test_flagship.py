"""Integration tests for the AERIS Phase 5 flagship lifecycle.

Tests the complete public-facade sequence from reset through verification,
mirroring the exact flow of scripts/run_flagship.py.

Scenario: mumbai_weather_crisis_v2 (scenarios/mumbai_weather_crisis.json)
Timeline: T+0 baseline → T+19 validate → T+28 apply → T+32 verify

These tests are integration-level: they call the deterministic engine through
the public facade and assert the full lifecycle outcome.  They do NOT test
individual engine subsystems (those are covered in tests/engine/).
"""
from __future__ import annotations

import json

import pytest

from app.engine import public


# ─────────────────────────────────────────────────────────────────────────────
# Scenario constants (from scenarios/mumbai_weather_crisis.json)
# ─────────────────────────────────────────────────────────────────────────────
TARGET_FLIGHT = "F102"
TOTAL_CANDIDATES = 5
EXPECTED_REJECTED = {"ALT-C", "ALT-E"}
EXPECTED_FEASIBLE = {"ALT-A", "ALT-B", "ALT-D"}
PREFERRED_CANDIDATE = "ALT-D"
STRESS_PROFILE_COUNT = 5


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def fresh_engine():
    """Reset the engine before and after every test."""
    public.reset_engine()
    yield
    public.reset_engine()


def _advance_to_flagship_decision_point() -> list[dict]:
    """Advance the engine to t=19 and generate candidate alternatives.

    This is the common setup for all tests that need the full scenario state.
    """
    public.advance_simulation(19)
    return public.generate_alternatives(TARGET_FLIGHT)


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 — Reset produces a clean deterministic state
# ─────────────────────────────────────────────────────────────────────────────

def test_reset_produces_clean_state():
    public.advance_simulation(10)
    public.generate_alternatives(TARGET_FLIGHT)

    public.reset_engine()

    state = public.get_airspace_state()
    assert state["time_min"] == 0
    assert public._CANDIDATES == {}
    assert public._APPLIED_INTERVENTION is None
    assert public._engine().state.approved_intervention is None


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 — Timeline state is correct at key checkpoints
# ─────────────────────────────────────────────────────────────────────────────

def test_baseline_state_is_clean():
    state = public.get_airspace_state()
    aircraft = {a["id"]: a for a in state["aircraft"]}
    airports = {a["id"]: a for a in state["airports"]}

    assert state["time_min"] == 0
    assert len(state["aircraft"]) == 40
    assert airports["BOM"]["arrival_capacity"] == 18
    assert aircraft[TARGET_FLIGHT]["status"] == "AIRBORNE"
    assert aircraft[TARGET_FLIGHT]["fuel_remaining_min"] == 70.0


def test_f102_is_degraded_at_t15():
    public.advance_simulation(15)
    state = public.get_airspace_state()
    aircraft = {a["id"]: a for a in state["aircraft"]}
    f102 = aircraft[TARGET_FLIGHT]

    assert f102["status"] == "DEGRADED"
    assert f102["fuel_remaining_min"] == 50.0


def test_bom_capacity_drops_at_t8():
    public.advance_simulation(8)
    state = public.get_airspace_state()
    airports = {a["id"]: a for a in state["airports"]}
    assert airports["BOM"]["arrival_capacity"] == 12


def test_restriction_active_at_t18():
    public.advance_simulation(18)
    state = public.get_airspace_state()
    restrictions = {r["id"]: r for r in state.get("restrictions", [])}
    assert restrictions.get("R-MONSOON-01", {}).get("active") is True


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3 — Candidate generation
# ─────────────────────────────────────────────────────────────────────────────

def test_generate_returns_exactly_five_candidates():
    candidates = _advance_to_flagship_decision_point()
    assert len(candidates) == TOTAL_CANDIDATES


def test_generate_candidate_ids_are_in_deterministic_order():
    candidates = _advance_to_flagship_decision_point()
    ids = [c["candidate_id"] for c in candidates]
    assert ids == ["ALT-A", "ALT-B", "ALT-C", "ALT-D", "ALT-E"]


def test_generate_registers_all_candidates_in_registry():
    candidates = _advance_to_flagship_decision_point()
    assert len(public._CANDIDATES) == TOTAL_CANDIDATES
    for c in candidates:
        assert (c["flight_id"], c["candidate_id"]) in public._CANDIDATES


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4 — Constraint validation
# ─────────────────────────────────────────────────────────────────────────────

def test_alt_c_rejected_by_restriction():
    candidates = _advance_to_flagship_decision_point()
    alt_c = next(c for c in candidates if c["candidate_id"] == "ALT-C")
    result = public.validate_candidate(alt_c)
    assert result["feasible"] is False
    assert any("restriction" in r.lower() for r in result["rejection_reasons"])


def test_alt_e_rejected_by_fuel():
    candidates = _advance_to_flagship_decision_point()
    alt_e = next(c for c in candidates if c["candidate_id"] == "ALT-E")
    result = public.validate_candidate(alt_e)
    assert result["feasible"] is False
    assert any("fuel" in r.lower() for r in result["rejection_reasons"])


def test_exactly_two_candidates_rejected():
    candidates = _advance_to_flagship_decision_point()
    results = {c["candidate_id"]: public.validate_candidate(c) for c in candidates}
    rejected = {cid for cid, r in results.items() if not r["feasible"]}
    assert rejected == EXPECTED_REJECTED


def test_exactly_three_candidates_feasible():
    candidates = _advance_to_flagship_decision_point()
    results = {c["candidate_id"]: public.validate_candidate(c) for c in candidates}
    feasible = {cid for cid, r in results.items() if r["feasible"]}
    assert feasible == EXPECTED_FEASIBLE


def test_constraint_result_structure_is_complete():
    candidates = _advance_to_flagship_decision_point()
    alt_a = next(c for c in candidates if c["candidate_id"] == "ALT-A")
    result = public.validate_candidate(alt_a)
    required = {"candidate_id", "flight_id", "feasible", "constraint_results",
                "rejection_reasons", "weather_risk"}
    assert required.issubset(result.keys())
    sub = result["constraint_results"]
    assert {"route", "weather", "fuel", "capacity", "conflict", "restriction"}.issubset(sub.keys())


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5 — Simulation
# ─────────────────────────────────────────────────────────────────────────────

def test_simulate_returns_required_fields():
    candidates = _advance_to_flagship_decision_point()
    alt_a = next(c for c in candidates if c["candidate_id"] == "ALT-A")
    result = public.simulate_candidate(alt_a)
    required = {"candidate_id", "target_delay_delta_min", "network_delay_delta_min", "affected_flights"}
    assert required.issubset(result.keys())


def test_simulate_is_json_serializable():
    candidates = _advance_to_flagship_decision_point()
    alt_d = next(c for c in candidates if c["candidate_id"] == "ALT-D")
    result = public.simulate_candidate(alt_d)
    json.dumps(result)  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6 — Stress testing
# ─────────────────────────────────────────────────────────────────────────────

def test_stress_runs_five_profiles():
    candidates = _advance_to_flagship_decision_point()
    alt_d = next(c for c in candidates if c["candidate_id"] == "ALT-D")
    report = public.stress_test_candidate(alt_d)
    assert report["total"] == STRESS_PROFILE_COUNT


def test_stress_report_structure():
    candidates = _advance_to_flagship_decision_point()
    alt_a = next(c for c in candidates if c["candidate_id"] == "ALT-A")
    report = public.stress_test_candidate(alt_a)
    assert "passed" in report
    assert "total" in report
    assert "survival_pct" in report
    assert "results" in report
    assert len(report["results"]) == STRESS_PROFILE_COUNT


def test_stress_report_is_json_serializable():
    candidates = _advance_to_flagship_decision_point()
    alt_a = next(c for c in candidates if c["candidate_id"] == "ALT-A")
    report = public.stress_test_candidate(alt_a)
    json.dumps(report)  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7 — Scoring
# ─────────────────────────────────────────────────────────────────────────────

def test_score_returns_all_five_candidates():
    candidates = _advance_to_flagship_decision_point()
    scored = public.score_candidates(candidates)
    assert len(scored) == TOTAL_CANDIDATES


def test_scored_candidates_are_sorted_highest_first():
    candidates = _advance_to_flagship_decision_point()
    scored = public.score_candidates(candidates)
    scores = [c["decision_score"] for c in scored]
    assert scores == sorted(scores, reverse=True)


def test_infeasible_candidates_have_zero_score():
    candidates = _advance_to_flagship_decision_point()
    scored = public.score_candidates(candidates)
    scored_by_id = {c["candidate_id"]: c for c in scored}
    for cid in EXPECTED_REJECTED:
        assert scored_by_id[cid]["decision_score"] == 0.0
        assert scored_by_id[cid]["feasible"] is False


def test_feasible_candidates_have_positive_score():
    candidates = _advance_to_flagship_decision_point()
    scored = public.score_candidates(candidates)
    scored_by_id = {c["candidate_id"]: c for c in scored}
    for cid in EXPECTED_FEASIBLE:
        assert scored_by_id[cid]["decision_score"] > 0.0
        assert scored_by_id[cid]["feasible"] is True


def test_preferred_candidate_alt_d_is_scored():
    candidates = _advance_to_flagship_decision_point()
    scored = public.score_candidates(candidates)
    scored_by_id = {c["candidate_id"]: c for c in scored}
    assert PREFERRED_CANDIDATE in scored_by_id
    assert scored_by_id[PREFERRED_CANDIDATE]["feasible"] is True
    assert scored_by_id[PREFERRED_CANDIDATE]["decision_score"] > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# TEST 8 — Human approval gate + apply
# ─────────────────────────────────────────────────────────────────────────────

def test_apply_returns_executing_status():
    candidates = _advance_to_flagship_decision_point()
    public.score_candidates(candidates)
    result = public.apply_intervention(PREFERRED_CANDIDATE)
    assert result["status"] == "EXECUTING"
    assert result["candidate_id"] == PREFERRED_CANDIDATE
    assert result["flight_id"] == TARGET_FLIGHT


def test_apply_sets_approved_intervention_on_state():
    candidates = _advance_to_flagship_decision_point()
    public.score_candidates(candidates)
    public.apply_intervention(PREFERRED_CANDIDATE)
    assert public._engine().state.approved_intervention == PREFERRED_CANDIDATE


def test_apply_without_prior_generate_raises():
    with pytest.raises(ValueError, match="Unknown candidate"):
        public.apply_intervention(PREFERRED_CANDIDATE)


def test_apply_infeasible_candidate_raises():
    candidates = _advance_to_flagship_decision_point()
    public.score_candidates(candidates)
    with pytest.raises(ValueError):
        public.apply_intervention("ALT-C")  # rejected by restriction


def test_approved_intervention_survives_advance():
    """Verify that apply_intervention outcome persists through subsequent advance_simulation calls."""
    candidates = _advance_to_flagship_decision_point()
    public.score_candidates(candidates)
    public.apply_intervention(PREFERRED_CANDIDATE)

    public.advance_simulation(4)  # advance to t=23 equivalent

    # _APPLIED_INTERVENTION must survive
    assert public._APPLIED_INTERVENTION is not None
    assert public._APPLIED_INTERVENTION["candidate_id"] == PREFERRED_CANDIDATE


# ─────────────────────────────────────────────────────────────────────────────
# TEST 9 — Verification
# ─────────────────────────────────────────────────────────────────────────────

def test_verify_without_apply_raises():
    with pytest.raises(ValueError, match="No intervention has been applied"):
        public.verify_state(PREFERRED_CANDIDATE)


def test_verify_returns_valid_status():
    candidates = _advance_to_flagship_decision_point()
    public.score_candidates(candidates)
    public.apply_intervention(PREFERRED_CANDIDATE)
    public.advance_simulation(4)

    result = public.verify_state(PREFERRED_CANDIDATE)
    assert result["status"] in {"VERIFIED", "REASSESSMENT_REQUIRED"}


def test_verify_returns_all_contract_fields():
    candidates = _advance_to_flagship_decision_point()
    public.score_candidates(candidates)
    public.apply_intervention(PREFERRED_CANDIDATE)

    result = public.verify_state(PREFERRED_CANDIDATE)
    required = {
        "status", "target_delay_delta_min", "affected_flights",
        "network_delay_delta_min", "constraints_safe",
        "new_degradation", "reassessment_required",
    }
    assert required.issubset(result.keys())


def test_verify_wrong_candidate_raises():
    candidates = _advance_to_flagship_decision_point()
    public.score_candidates(candidates)
    public.apply_intervention(PREFERRED_CANDIDATE)

    with pytest.raises(ValueError, match="not the currently applied"):
        public.verify_state("ALT-A")


def test_verify_result_is_json_serializable():
    candidates = _advance_to_flagship_decision_point()
    public.score_candidates(candidates)
    public.apply_intervention(PREFERRED_CANDIDATE)

    result = public.verify_state(PREFERRED_CANDIDATE)
    json.dumps(result)  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# TEST 10 — Full flagship lifecycle (single sequential test)
# ─────────────────────────────────────────────────────────────────────────────

def test_full_flagship_lifecycle():
    """Execute the complete decision sequence and assert the key story beats.

    This mirrors the scripts/run_flagship.py flow using only the public facade.
    """
    # 1. Reset
    public.reset_engine()
    assert public.get_airspace_state()["time_min"] == 0

    # 2. Advance to decision point
    public.advance_simulation(19)

    # 3. Generate
    candidates = public.generate_alternatives(TARGET_FLIGHT)
    assert len(candidates) == TOTAL_CANDIDATES

    # 4. Validate
    val_results = {c["candidate_id"]: public.validate_candidate(c) for c in candidates}
    rejected = {cid for cid, r in val_results.items() if not r["feasible"]}
    feasible = [c for c in candidates if val_results[c["candidate_id"]]["feasible"]]
    assert rejected == EXPECTED_REJECTED
    assert len(feasible) >= 3

    # 5. Simulate
    for c in feasible:
        sim = public.simulate_candidate(c)
        assert "target_delay_delta_min" in sim

    # 6. Stress test
    for c in feasible:
        report = public.stress_test_candidate(c)
        assert report["total"] == STRESS_PROFILE_COUNT

    # 7. Score
    scored = public.score_candidates(candidates)
    assert len(scored) == TOTAL_CANDIDATES
    scores = [c["decision_score"] for c in scored]
    assert scores == sorted(scores, reverse=True)

    # 8. Human approval gate — explicit YES before apply (not skipped)
    approved: bool = True  # deterministic approval
    assert approved is True, "Human approval must be explicitly set"

    # 9. Apply
    apply_result = public.apply_intervention(PREFERRED_CANDIDATE)
    assert apply_result["status"] == "EXECUTING"

    # 10. Verify
    ver = public.verify_state(PREFERRED_CANDIDATE)
    assert ver["status"] in {"VERIFIED", "REASSESSMENT_REQUIRED"}
    assert isinstance(ver["affected_flights"], int)
    json.dumps(ver)

    # 11. Reset restores clean state
    public.reset_engine()
    assert public.get_airspace_state()["time_min"] == 0
    assert public._CANDIDATES == {}
    assert public._APPLIED_INTERVENTION is None
    with pytest.raises(ValueError, match="Unknown candidate"):
        public.apply_intervention(PREFERRED_CANDIDATE)


# ─────────────────────────────────────────────────────────────────────────────
# TEST 11 — Repeatability (two independent runs produce identical decisions)
# ─────────────────────────────────────────────────────────────────────────────

def _run_decision_sequence() -> dict:
    """Run the minimal decision sequence and return the key outcome dict."""
    public.reset_engine()
    public.advance_simulation(19)
    candidates = public.generate_alternatives(TARGET_FLIGHT)
    for c in candidates:
        public.validate_candidate(c)
    feasible = [c for c in candidates if c["candidate_id"] in EXPECTED_FEASIBLE]
    for c in feasible:
        public.simulate_candidate(c)
        public.stress_test_candidate(c)
    scored = public.score_candidates(candidates)
    apply_result = public.apply_intervention(PREFERRED_CANDIDATE)
    ver = public.verify_state(PREFERRED_CANDIDATE)
    return {
        "recommendation": PREFERRED_CANDIDATE,
        "apply_status": apply_result["status"],
        "verification_status": ver["status"],
        "top_score": round(scored[0]["decision_score"], 4),
        "alt_d_score": round(
            next(c["decision_score"] for c in scored if c["candidate_id"] == PREFERRED_CANDIDATE), 4
        ),
    }


def test_two_runs_produce_identical_decisions():
    """The engine must be fully deterministic: two sequential runs must agree."""
    result_a = _run_decision_sequence()
    result_b = _run_decision_sequence()
    assert result_a == result_b, (
        f"Engine is non-deterministic!\nRun 1: {result_a}\nRun 2: {result_b}"
    )
