import json
import math
import pytest
from shapely.geometry import Polygon

from app.engine.digital_twin.loaders import load_world
from app.engine.digital_twin.simulator import DigitalTwinSimulator
from app.engine.routes.generator import generate_candidate_routes
from app.engine.stress_test.report import summarize_stress_test
from app.engine.stress_test.runner import run_stress_test
from app.engine.stress_test.scenarios import build_stress_scenarios, perturb_state


def test_exactly_five_stress_scenarios_from_flagship():
    state = load_world()
    scenarios = build_stress_scenarios(state)
    assert len(scenarios) == 5


def test_stress_scenario_ids():
    state = load_world()
    scenarios = build_stress_scenarios(state)
    ids = [s["id"] for s in scenarios]
    assert ids == ["F1", "F2", "F3", "F4", "F5"]


def test_stress_scenario_names():
    state = load_world()
    scenarios = build_stress_scenarios(state)
    expected_names = [
        "Weather expansion +10%",
        "Weather expansion +20%",
        "S6 capacity -15%",
        "Traffic demand +15%",
        "BOM acceptance -20%",
    ]
    names = [s["name"] for s in scenarios]
    assert names == expected_names


def test_stress_profiles_deterministic_order():
    state = load_world()
    s1 = build_stress_scenarios(state)
    s2 = build_stress_scenarios(state)
    assert [s["id"] for s in s1] == [s["id"] for s in s2]


def test_perturb_state_does_not_mutate_original_state():
    state = load_world()
    snap_before = state.snapshot()
    profile = {"weather_expand_factor": 1.20}
    perturbed = perturb_state(state, profile)
    assert state.snapshot() == snap_before
    assert perturbed is not state


def test_weather_expansion_changes_polygon_geometry_and_area():
    state = load_world()
    cell_before = state.weather_cells["WX-BOM-01"]
    poly_before = Polygon(cell_before.geometry["coordinates"][0])

    profile = {"weather_expand_factor": 1.20}
    perturbed = perturb_state(state, profile)
    poly_after = Polygon(perturbed.weather_cells["WX-BOM-01"].geometry["coordinates"][0])

    assert poly_after.area > poly_before.area


def test_sector_capacity_perturbation_is_deterministic():
    state = load_world()
    old_cap = state.sectors["S6"].capacity
    profile = {"sector_capacity_factor": {"S6": 0.85}}
    p1 = perturb_state(state, profile)
    p2 = perturb_state(state, profile)
    expected = max(1, int(round(old_cap * 0.85)))
    assert p1.sectors["S6"].capacity == expected
    assert p2.sectors["S6"].capacity == expected


def test_traffic_perturbation_is_deterministic():
    state = load_world()
    profile = {"traffic_factor": 1.15}
    p1 = perturb_state(state, profile)
    p2 = perturb_state(state, profile)
    assert p1.sectors["S1"].forecast_traffic == p2.sectors["S1"].forecast_traffic


def test_airport_capacity_perturbation_is_deterministic():
    state = load_world()
    old_cap = state.airports["BOM"].arrival_capacity
    profile = {"airport_capacity_factor": {"BOM": 0.80}}
    p1 = perturb_state(state, profile)
    expected = max(1, int(round(old_cap * 0.80)))
    assert p1.airports["BOM"].arrival_capacity == expected


def test_invalid_stress_factor_raises_value_error():
    state = load_world()
    with pytest.raises(ValueError):
        perturb_state(state, {"weather_expand_factor": -1.0})
    with pytest.raises(ValueError):
        perturb_state(state, {"traffic_factor": math.nan})
    with pytest.raises(ValueError):
        perturb_state(state, {"sector_capacity_factor": {"S6": -0.5}})


def test_candidate_validated_in_every_stress_scenario():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(21)
    candidates = generate_candidate_routes(sim.state.graph, "F102")
    res = run_stress_test(sim.state, candidates[0])
    for r in res:
        assert "constraint_failures" in r


def test_hard_constraint_failure_causes_stress_failure():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(21)
    sim.state.aircraft["F102"].fuel_remaining_min = 0.0
    candidates = generate_candidate_routes(sim.state.graph, "F102")
    res = run_stress_test(sim.state, candidates[0])
    for r in res:
        assert r["passed"] is False
        assert "HARD_CONSTRAINT: fuel" in r["failure_reasons"]


def test_new_conflict_causes_stress_failure():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(21)
    candidate = {
        "candidate_id": "ALT-DEV",
        "flight_id": "F102",
        "route": ["W0", "W4", "W5", "W7", "BOM"],
        "speed_kt": 430.0,
    }

    other = sim.state.aircraft["AI2-01"]
    other.route = ["W0", "W4", "W5", "W7", "BOM"]
    other.route_index = 0
    other.edge_progress_min = 0.0
    other.status = "AIRBORNE"
    other.speed_kt = 430.0

    res = run_stress_test(sim.state, candidate)
    for r in res:
        assert r["passed"] is False
        assert "HARD_CONSTRAINT: conflict" in r["failure_reasons"] or "CONFLICT: new conflict predicted" in r["failure_reasons"]


def test_target_delay_over_25_causes_stress_failure():
    r = {
        "scenario_id": "TEST",
        "scenario_name": "TEST",
        "passed": False,
        "target_delay_delta_min": 30.0,
        "network_delay_delta_min": 5.0,
        "max_sector_utilization_pct": 50.0,
        "new_conflicts": 0,
        "failure_reasons": ["TARGET: delay_delta > 25.0"],
    }
    rep = summarize_stress_test([r])
    assert rep["passed"] == 0
    assert "target delay delta 30.0 min" in rep["failures"][0]["reason"]


def test_network_delay_over_25_causes_stress_failure():
    r = {
        "scenario_id": "TEST",
        "scenario_name": "TEST",
        "passed": False,
        "target_delay_delta_min": 5.0,
        "network_delay_delta_min": 31.2,
        "max_sector_utilization_pct": 50.0,
        "new_conflicts": 0,
        "failure_reasons": ["NETWORK: delay_delta > 25.0"],
    }
    rep = summarize_stress_test([r])
    assert rep["passed"] == 0
    assert "network delay delta 31.2 min" in rep["failures"][0]["reason"]


def test_max_sector_utilization_over_100_causes_stress_failure():
    r = {
        "scenario_id": "TEST",
        "scenario_name": "TEST",
        "passed": False,
        "target_delay_delta_min": 5.0,
        "network_delay_delta_min": 5.0,
        "max_sector_utilization_pct": 115.0,
        "new_conflicts": 0,
        "failure_reasons": ["NETWORK: sector utilization > 100%"],
    }
    rep = summarize_stress_test([r])
    assert rep["passed"] == 0
    assert "sector utilization 115.0%" in rep["failures"][0]["reason"]


def test_high_weather_alone_does_not_automatically_fail_scenario():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(5)
    candidates = generate_candidate_routes(sim.state.graph, "F102")
    alt_c = [c for c in candidates if c["candidate_id"] == "ALT-C"][0]
    res = run_stress_test(sim.state, alt_c)
    f1_res = [r for r in res if r["scenario_id"] == "F1"][0]
    assert f1_res["weather_risk"] == "HIGH"
    assert "HARD_CONSTRAINT: weather" not in f1_res["failure_reasons"]


def test_every_failed_scenario_contains_at_least_one_failure_reason():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(21)
    sim.state.aircraft["F102"].fuel_remaining_min = 0.0
    candidates = generate_candidate_routes(sim.state.graph, "F102")
    res = run_stress_test(sim.state, candidates[0])
    for r in res:
        if not r["passed"]:
            assert len(r["failure_reasons"]) > 0


def test_failure_reasons_correspond_to_actual_failure_conditions():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(21)
    sim.state.aircraft["F102"].fuel_remaining_min = 0.0
    candidates = generate_candidate_routes(sim.state.graph, "F102")
    report = summarize_stress_test(run_stress_test(sim.state, candidates[0]))
    for f in report["failures"]:
        assert "Fuel hard constraint failed" in f["reason"]


def test_report_survival_percentage_is_correct():
    results = [{"passed": True}, {"passed": True}, {"passed": False}, {"passed": False}]
    rep = summarize_stress_test(results)
    assert rep["passed"] == 2
    assert rep["total"] == 4
    assert rep["survival_pct"] == 50.0


def test_report_handles_zero_scenarios_safely():
    rep = summarize_stress_test([])
    assert rep["passed"] == 0
    assert rep["total"] == 0
    assert rep["survival_pct"] == 0.0
    assert rep["failures"] == []


def test_stress_test_is_repeatable():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(21)
    candidate = [c for c in generate_candidate_routes(sim.state.graph, "F102") if c["candidate_id"] == "ALT-D"][0]
    a = summarize_stress_test(run_stress_test(sim.state, candidate))
    b = summarize_stress_test(run_stress_test(sim.state, candidate))
    assert a == b
    assert a["total"] == 5


def test_run_stress_test_does_not_mutate_input_state():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(21)
    snap_before = sim.state.snapshot()
    candidate = generate_candidate_routes(sim.state.graph, "F102")[0]
    run_stress_test(sim.state, candidate)
    assert sim.state.snapshot() == snap_before


def test_all_returned_results_are_json_serializable():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(21)
    candidate = generate_candidate_routes(sim.state.graph, "F102")[0]
    results = run_stress_test(sim.state, candidate)
    json_str = json.dumps(results)
    assert isinstance(json_str, str)


def test_five_stress_scenarios_preserved_even_on_failures():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(21)
    sim.state.aircraft["F102"].fuel_remaining_min = 0.0
    candidate = generate_candidate_routes(sim.state.graph, "F102")[0]
    results = run_stress_test(sim.state, candidate)
    assert len(results) == 5
