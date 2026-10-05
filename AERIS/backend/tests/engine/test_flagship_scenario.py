from __future__ import annotations

from copy import deepcopy

import pytest

from app.engine import public
from app.engine.digital_twin.loaders import load_scenario, load_world
from app.engine.digital_twin.simulator import DigitalTwinSimulator
from app.engine.stress_test.runner import run_stress_test


@pytest.fixture(autouse=True)
def reset_public_engine():
    public.reset_engine()
    yield
    public.reset_engine()


def _score_at_decision_time() -> list[dict]:
    public.reset_engine()
    public.advance_simulation(19)
    candidates = public.generate_alternatives("F102")
    public.begin_decision_context(["F102"], candidates)
    return public.score_candidates(candidates)


def test_flagship_timeline_and_disruptions_are_deterministic_through_t35():
    scenario = load_scenario()
    assert scenario["target_flight_id"] == "F102"
    assert scenario["simulation_minutes"] == 35

    simulator = DigitalTwinSimulator(load_world())
    state = simulator.state
    assert state.time_min == 0
    assert state.aircraft["F102"].status == "AIRBORNE"
    assert state.weather_cells["WX-BOM-01"].intensity == "MODERATE"

    simulator.advance(5)
    assert state.time_min == 5
    assert state.weather_cells["WX-BOM-01"].intensity == "HIGH"

    simulator.advance(3)
    assert state.airports["BOM"].arrival_capacity == 12

    simulator.advance(2)
    assert state.holding_flights == {"AI2-01", "AI3-01", "AI5-01", "AI8-01"}

    simulator.advance(2)
    assert state.sectors["S6"].capacity == 6

    simulator.advance(3)
    assert state.aircraft["F102"].status == "DEGRADED"
    assert 0 < state.aircraft["F102"].fuel_remaining_min <= 51

    simulator.advance(3)
    assert state.restrictions["R-MONSOON-01"].active is True

    simulator.advance(17)
    assert state.time_min == 35


def test_scenario_loads_and_stress_testing_do_not_mutate_source_world():
    source_scenario = load_scenario()
    state = load_world()
    state_snapshot = state.snapshot()
    scenario_snapshot = deepcopy(state.scenario)

    state.scenario["events"][0]["t"] = -1
    assert load_scenario() == source_scenario
    state.scenario = deepcopy(scenario_snapshot)

    simulator = DigitalTwinSimulator(state)
    simulator.advance(19)
    state_snapshot = state.snapshot()
    scenario_snapshot = deepcopy(state.scenario)
    candidate = next(
        item for item in public.generate_alternatives("F102")
        if item["candidate_id"] == "ALT-D"
    )

    first = run_stress_test(state, candidate)
    second = run_stress_test(state, candidate)

    assert first == second
    assert state.snapshot() == state_snapshot
    assert state.scenario == scenario_snapshot


def test_flagship_candidate_validation_contract_and_route_diversity():
    public.advance_simulation(19)
    candidates = public.generate_alternatives("F102")
    assert [item["candidate_id"] for item in candidates] == ["ALT-A", "ALT-B", "ALT-C", "ALT-D", "ALT-E"]
    assert len({tuple(item["route"]) for item in candidates}) == 5
    assert all(item["flight_id"] == "F102" for item in candidates)
    decision_node = public._engine().state.aircraft["F102"].route[
        public._engine().state.aircraft["F102"].route_index
    ]
    assert all(item["route"][0] == decision_node for item in candidates)
    assert all(item["route_valid"] for item in candidates)

    validations = {
        item["candidate_id"]: public.validate_candidate(item)
        for item in candidates
    }
    assert validations["ALT-C"]["feasible"] is False
    assert validations["ALT-C"]["constraint_results"]["restriction"]["passed"] is False
    assert any("restriction" in reason.lower() or "temporary" in reason.lower()
               for reason in validations["ALT-C"]["rejection_reasons"])

    assert validations["ALT-E"]["feasible"] is False
    assert validations["ALT-E"]["constraint_results"]["fuel"]["feasible"] is False

    assert validations["ALT-A"]["feasible"] is True
    assert validations["ALT-B"]["feasible"] is True
    assert validations["ALT-D"]["feasible"] is True


def test_flagship_stress_profiles_are_five_deterministic_and_numerically_distinct():
    scored = _score_at_decision_time()
    by_id = {item["candidate_id"]: item for item in scored}
    assert len(by_id) == 5

    feasible_ids = {candidate_id for candidate_id, item in by_id.items() if item["feasible"]}
    assert feasible_ids == {"ALT-A", "ALT-B", "ALT-D"}
    assert [item["scenario_id"] for item in by_id["ALT-D"]["stress_report"]["results"]] == [
        "F1", "F2", "F3", "F4", "F5"
    ]
    stress_profiles = {profile["id"]: profile for profile in load_scenario()["stress_profiles"]}
    assert "R-FUTURE-S6-01" in stress_profiles["F3"]["activate_restrictions"]
    alt_b_f3 = next(
        item for item in by_id["ALT-B"]["stress_report"]["results"]
        if item["scenario_id"] == "F3"
    )
    alt_d_f3 = next(
        item for item in by_id["ALT-D"]["stress_report"]["results"]
        if item["scenario_id"] == "F3"
    )
    assert "HARD_CONSTRAINT: restriction" in alt_b_f3["failure_reasons"]
    assert alt_d_f3["passed"] is True

    for candidate_id in feasible_ids:
        candidate = next(item for item in public._CANDIDATES.values()
                         if item.get("candidate_id") == candidate_id)
        stress = public.stress_test_candidate(candidate)
        assert len(stress["results"]) == 5
        assert stress == public.stress_test_candidate(candidate)

    candidate_stress_deltas = {
        candidate_id: by_id[candidate_id]["stress_report"]["results"][0]["network_delay_delta_min"]
        for candidate_id in feasible_ids
    }
    assert len(set(candidate_stress_deltas.values())) > 1

    for candidate_id in feasible_ids:
        candidate = by_id[candidate_id]
        assert "target_flight_benefit" in candidate["network_metrics"]
        assert "network_ripple_cost" in candidate["network_metrics"]
        assert "future_robustness" in candidate["resilience_metrics"]
        assert "reintervention_probability" in candidate["resilience_metrics"]
        assert "regret" in candidate["resilience_metrics"]


def test_repeated_clean_flagship_runs_return_identical_candidate_metrics():
    first = _score_at_decision_time()
    second = _score_at_decision_time()
    assert first == second
    assert [candidate["decision_context"]["snapshot_id"] for candidate in first] == [
        candidate["decision_context"]["snapshot_id"] for candidate in second
    ]


def test_candidates_begin_at_f102_decision_position():
    public.advance_simulation(19)
    target = public._engine().state.aircraft["F102"]
    decision_node = target.route[target.route_index]
    candidates = public.generate_alternatives("F102")

    assert all(candidate["route"][0] == decision_node for candidate in candidates)


def test_alt_d_has_strongest_resilience_and_wins_engine_score():
    scored = _score_at_decision_time()
    by_id = {item["candidate_id"]: item for item in scored}

    assert by_id["ALT-A"]["target_delay_min"] < by_id["ALT-D"]["target_delay_min"]
    assert by_id["ALT-A"]["network_delay_delta_min"] > by_id["ALT-D"]["network_delay_delta_min"]
    assert by_id["ALT-A"]["network_metrics"]["network_ripple_cost"] > by_id["ALT-D"]["network_metrics"]["network_ripple_cost"]
    assert by_id["ALT-A"]["stress_survival"]["passed"] < by_id["ALT-D"]["stress_survival"]["passed"]
    assert by_id["ALT-D"]["resilience_metrics"]["future_robustness"] > by_id["ALT-A"]["resilience_metrics"]["future_robustness"]
    assert by_id["ALT-D"]["decision_score"] > by_id["ALT-A"]["decision_score"]
    ranked_feasible = [candidate for candidate in scored if candidate["feasible"]]
    assert scored[0]["candidate_id"] == ranked_feasible[0]["candidate_id"] == "ALT-D"
    assert len({candidate["decision_context"]["snapshot_id"] for candidate in scored}) == 1
    assert all(
        candidate["decision_context"]["snapshot_id"] == candidate["decision_context_id"]
        for candidate in scored
    )
    context_id = scored[0]["decision_context"]["snapshot_id"]
    context_evidence = public.get_decision_context(context_id)["candidates"]
    feasible_ids = {candidate_id for candidate_id, candidate in by_id.items() if candidate["feasible"]}
    for candidate_id in feasible_ids:
        evidence = context_evidence[candidate_id]
        assert evidence["validation"] == by_id[candidate_id]["decision_context"]["validation"]
        assert evidence["simulation"] == by_id[candidate_id]["decision_context"]["simulation"]
        assert evidence["stress_report"] == by_id[candidate_id]["decision_context"]["stress_report"]


def test_flagship_scenario_contains_no_explicit_preferred_candidate_and_alt_d_wins_naturally():
    scenario = load_scenario()
    recommend_events = [
        event for event in scenario.get("events", [])
        if "recommend" in event.get("event", "") or event.get("t") == 28
    ]
    assert len(recommend_events) > 0
    forbidden_fields = {"preferred", "forced_candidate", "winner", "candidate_override", "preferred_candidate"}
    for event in scenario.get("events", []):
        payload = event.get("payload", {})
        for field in forbidden_fields:
            assert field not in payload, f"Scenario event '{event.get('event')}' contains explicit candidate selection field '{field}'"

    scored = _score_at_decision_time()
    ranked_feasible = [c for c in scored if c.get("feasible")]
    assert len(ranked_feasible) > 0
    top_candidate = ranked_feasible[0]
    assert top_candidate["candidate_id"] == "ALT-D"
    assert top_candidate["decision_score"] > ranked_feasible[1]["decision_score"]

