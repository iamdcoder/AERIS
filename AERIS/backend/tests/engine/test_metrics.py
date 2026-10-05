import math
import pytest

from app.engine.metrics.network import network_impact_metrics
from app.engine.metrics.resilience import resilience_metrics
from app.engine.metrics.score import score_candidate


# ==================================================
# NETWORK METRIC TESTS
# ==================================================

def test_network_impact_zero_impact():
    sim = {}
    res = network_impact_metrics(sim)
    assert res["target_flight_benefit"] == 0
    assert res["network_ripple_cost"] == 0
    assert res["affected_flights"] == 0


def test_network_impact_target_improvement():
    sim = {"target_delay_delta_min": -6}
    res = network_impact_metrics(sim)
    assert res["target_flight_benefit"] == 6


def test_network_impact_target_worsening():
    sim = {"target_delay_delta_min": 6}
    res = network_impact_metrics(sim)
    assert res["target_flight_benefit"] == 0


def test_network_impact_ripple_cost():
    sim = {"network_delay_delta_min": 5, "affected_flights": 4}
    res = network_impact_metrics(sim)
    assert res["network_ripple_cost"] == 7  # 5 + 4*0.5 = 7


def test_network_impact_negative_network_delay():
    sim = {"network_delay_delta_min": -5, "affected_flights": 2}
    res = network_impact_metrics(sim)
    assert res["network_ripple_cost"] == 1.0  # max(0, -5) + 2*0.5 = 1.0


def test_network_impact_missing_optional_fields():
    res = network_impact_metrics({})
    assert isinstance(res, dict)
    assert res["target_flight_benefit"] == 0
    assert res["network_ripple_cost"] == 0
    assert res["max_sector_utilization_pct"] == 0
    assert res["new_conflicts"] == 0


# ==================================================
# RESILIENCE TESTS
# ==================================================

def test_resilience_100_pct_survival():
    stress = {"survival_pct": 100}
    res = resilience_metrics(stress, {})
    assert res["future_robustness"] == 1.0
    assert res["reintervention_probability"] == 0.0


def test_resilience_50_pct_survival():
    stress = {"survival_pct": 50}
    res = resilience_metrics(stress, {})
    assert res["future_robustness"] == 0.5
    assert res["reintervention_probability"] == 0.5


def test_resilience_0_pct_survival():
    stress = {"survival_pct": 0}
    res = resilience_metrics(stress, {})
    assert res["future_robustness"] == 0.0
    assert res["reintervention_probability"] == 1.0


def test_resilience_no_stress_results():
    stress = {"survival_pct": 80, "results": []}
    res = resilience_metrics(stress, {})
    assert res["worst_case_network_delay_delta_min"] == 0.0
    assert res["regret"] == 0.0


def test_resilience_multiple_stress_results():
    stress = {
        "survival_pct": 80,
        "results": [
            {"network_delay_delta_min": -5},
            {"network_delay_delta_min": 10},
            {"network_delay_delta_min": 25},
        ],
    }
    res = resilience_metrics(stress, {})
    assert res["worst_case_network_delay_delta_min"] == 25.0
    assert res["regret"] == 0.25


def test_resilience_negative_only_stress_results():
    stress = {
        "survival_pct": 80,
        "results": [
            {"network_delay_delta_min": -10},
            {"network_delay_delta_min": -5},
        ],
    }
    res = resilience_metrics(stress, {})
    assert res["regret"] == 0.0


# ==================================================
# SCORE TESTS
# ==================================================

def test_score_is_bounded():
    net = {"target_flight_benefit": 20.0, "network_ripple_cost": 0.0}
    fuel = {"reserve_margin_min": 50.0}
    res = {"future_robustness": 1.0, "reintervention_probability": 0.0}

    score = score_candidate(net, fuel, res)
    assert 0.0 <= score <= 1.0


def test_score_identical_inputs():
    net = {"target_flight_benefit": 5.0, "network_ripple_cost": 2.0}
    fuel = {"reserve_margin_min": 15.0}
    res = {"future_robustness": 0.8, "reintervention_probability": 0.2}

    s1 = score_candidate(net, fuel, res)
    s2 = score_candidate(net, fuel, res)
    assert s1 == s2


def test_score_increasing_target_benefit_monotonic():
    fuel = {"reserve_margin_min": 10.0}
    res = {"future_robustness": 0.5, "reintervention_probability": 0.5}

    s1 = score_candidate({"target_flight_benefit": 2.0, "network_ripple_cost": 5.0}, fuel, res)
    s2 = score_candidate({"target_flight_benefit": 6.0, "network_ripple_cost": 5.0}, fuel, res)
    assert s2 >= s1


def test_score_increasing_fuel_reserve_monotonic():
    net = {"target_flight_benefit": 4.0, "network_ripple_cost": 5.0}
    res = {"future_robustness": 0.5, "reintervention_probability": 0.5}

    s1 = score_candidate(net, {"reserve_margin_min": 10.0}, res)
    s2 = score_candidate(net, {"reserve_margin_min": 25.0}, res)
    assert s2 >= s1


def test_score_increasing_future_robustness_monotonic():
    net = {"target_flight_benefit": 4.0, "network_ripple_cost": 5.0}
    fuel = {"reserve_margin_min": 10.0}

    s1 = score_candidate(net, fuel, {"future_robustness": 0.4, "reintervention_probability": 0.6})
    s2 = score_candidate(net, fuel, {"future_robustness": 0.9, "reintervention_probability": 0.1})
    assert s2 >= s1


def test_score_increasing_ripple_cost_decreases_score():
    fuel = {"reserve_margin_min": 10.0}
    res = {"future_robustness": 0.5, "reintervention_probability": 0.5}

    s1 = score_candidate({"target_flight_benefit": 4.0, "network_ripple_cost": 2.0}, fuel, res)
    s2 = score_candidate({"target_flight_benefit": 4.0, "network_ripple_cost": 10.0}, fuel, res)
    assert s2 <= s1


def test_score_increasing_reintervention_prob_does_not_improve_resilience():
    net = {"target_flight_benefit": 4.0, "network_ripple_cost": 5.0}
    fuel = {"reserve_margin_min": 10.0}

    s1 = score_candidate(net, fuel, {"future_robustness": 0.8, "reintervention_probability": 0.1})
    s2 = score_candidate(net, fuel, {"future_robustness": 0.8, "reintervention_probability": 0.9})
    assert s2 <= s1


def test_score_default_weights():
    net = {"target_flight_benefit": 6.0, "network_ripple_cost": 3.0}
    fuel = {"reserve_margin_min": 15.0}
    res = {"future_robustness": 0.8, "reintervention_probability": 0.2}

    # Should run with default weights when weights=None
    score_explicit = score_candidate(net, fuel, res, weights=None)
    assert isinstance(score_explicit, float)


def test_score_custom_weights():
    net = {"target_flight_benefit": 6.0, "network_ripple_cost": 3.0}
    fuel = {"reserve_margin_min": 15.0}
    res = {"future_robustness": 0.8, "reintervention_probability": 0.2}

    custom_w = {
        "target_flight_benefit": 1,
        "network_resilience": 0,
        "network_impact": 0,
        "fuel_margin": 0,
        "future_robustness": 0,
    }
    score = score_candidate(net, fuel, res, weights=custom_w)
    expected_target_component = round(6.0 / 12.0, 3)  # 0.5
    assert score == expected_target_component


def test_score_invalid_negative_custom_weight():
    with pytest.raises(ValueError):
        score_candidate({}, {}, {}, weights={"target_flight_benefit": -1})


def test_score_invalid_all_zero_custom_weights():
    all_zero = {
        "target_flight_benefit": 0,
        "network_resilience": 0,
        "network_impact": 0,
        "fuel_margin": 0,
        "future_robustness": 0,
    }
    with pytest.raises(ValueError):
        score_candidate({}, {}, {}, weights=all_zero)


def test_score_invalid_nan_inf_custom_weights():
    with pytest.raises(ValueError):
        score_candidate({}, {}, {}, weights={"target_flight_benefit": math.nan})

    with pytest.raises(ValueError):
        score_candidate({}, {}, {}, weights={"target_flight_benefit": math.inf})


# ==================================================
# DEFAULT SCORE REGRESSION TEST
# ==================================================

def test_default_score_regression():
    net = {"target_flight_benefit": 6.0, "network_ripple_cost": 3.0}
    fuel = {"reserve_margin_min": 15.0}
    res = {"future_robustness": 0.8, "reintervention_probability": 0.2}

    # Manual computation:
    # target = 6/12 = 0.5
    # network_impact = 1 - 3/15 = 0.8
    # fuel_margin = 15/30 = 0.5
    # future = 0.8
    # resilience_comp = 0.8 * (1 - 0.2) = 0.64
    # Expected weighted sum = 0.25*0.5 + 0.25*0.64 + 0.20*0.8 + 0.15*0.5 + 0.15*0.8
    # = 0.125 + 0.160 + 0.160 + 0.075 + 0.120 = 0.640
    assert score_candidate(net, fuel, res) == 0.640


# ==================================================
# DETERMINISM & IMMUTABILITY TEST
# ==================================================

def test_metrics_do_not_mutate_inputs():
    net = {"target_delay_delta_min": -5, "network_delay_delta_min": 2, "affected_flights": 3}
    net_copy = dict(net)

    stress = {"survival_pct": 75, "results": [{"network_delay_delta_min": 10}]}
    stress_copy = {"survival_pct": 75, "results": [{"network_delay_delta_min": 10}]}

    fuel = {"reserve_margin_min": 20.0}
    fuel_copy = dict(fuel)

    net_res = network_impact_metrics(net)
    res_res = resilience_metrics(stress, net)
    score = score_candidate(net_res, fuel, res_res)

    assert net == net_copy
    assert stress == stress_copy
    assert fuel == fuel_copy
