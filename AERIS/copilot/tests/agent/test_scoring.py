from copilot.agent.scoring import (
    DecisionScorer,
    DecisionWeights,
    ScoreNormalizationConfig,
)


def make_candidates():
    return [
        {
            "id": "ALT-A",
            "feasible": False,
            "target_delay_min": 2,
            "network_delay_delta_min": 9,
            "peak_sector_utilization": 1.08,
            "resilience": 0.41,
            "fuel_margin_kg": 700,
            "local_score": 0.98,
            "rejection_reasons": [
                "Sector S5 overload"
            ],
        },
        {
            "id": "ALT-B",
            "feasible": True,
            "target_delay_min": 4,
            "resilience": 0.66,
            "local_score": 0.96,
        },
        {
            "id": "ALT-C",
            "feasible": True,
            "target_delay_min": 5,
            "resilience": 0.81,
            "local_score": 0.88,
        },
        {
            "id": "ALT-D",
            "feasible": True,
            "target_delay_min": 8,
            "fuel_margin_kg": 610,
            "resilience": 0.91,
            "local_score": 0.82,
        },
        {
            "id": "ALT-E",
            "feasible": False,
            "target_delay_min": 10,
            "fuel_margin_kg": 388,
            "resilience": 0.94,
            "local_score": 0.75,
            "rejection_reasons": [
                "Fuel margin below hard minimum"
            ],
        },
    ]


def make_simulations():
    return [
        {
            "candidate_id": "ALT-B",
            "network_delay_delta_min": 2,
            "affected_flights": 4,
            "peak_sector_utilization": 0.94,
        },
        {
            "candidate_id": "ALT-C",
            "network_delay_delta_min": -3,
            "affected_flights": 3,
            "peak_sector_utilization": 0.86,
        },
        {
            "candidate_id": "ALT-D",
            "network_delay_delta_min": -14,
            "affected_flights": 1,
            "peak_sector_utilization": 0.82,
        },
    ]


def make_stress_tests():
    return [
        {
            "candidate_id": "ALT-B",
            "scenarios_passed": 3,
            "scenarios_total": 5,
        },
        {
            "candidate_id": "ALT-C",
            "scenarios_passed": 4,
            "scenarios_total": 5,
        },
        {
            "candidate_id": "ALT-D",
            "scenarios_passed": 5,
            "scenarios_total": 5,
        },
    ]


def test_weights_match_aeris_starting_model():
    weights = DecisionWeights()

    weights.validate_total()

    assert weights.target_flight_benefit == 0.25
    assert weights.network_resilience == 0.25
    assert weights.network_impact_score == 0.20
    assert weights.fuel_safety_margin == 0.15
    assert weights.future_robustness == 0.15


def test_weights_must_sum_to_one():
    weights = DecisionWeights(
        target_flight_benefit=0.50,
        network_resilience=0.50,
        network_impact_score=0.20,
        fuel_safety_margin=0.00,
        future_robustness=0.00,
    )

    try:
        weights.validate_total()
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Invalid weights should raise ValueError"
        )


def test_alt_d_becomes_network_resilient_winner():
    scorer = DecisionScorer()

    result = scorer.score_candidates(
        candidates=make_candidates(),
        simulations=make_simulations(),
        stress_tests=make_stress_tests(),
    )

    assert result.recommended_candidate_id == "ALT-D"


def test_infeasible_candidates_never_recommended():
    scorer = DecisionScorer()

    result = scorer.score_candidates(
        candidates=make_candidates(),
        simulations=make_simulations(),
        stress_tests=make_stress_tests(),
    )

    assert result.recommended_candidate_id not in {
        "ALT-A",
        "ALT-E",
    }


def test_score_components_are_normalized():
    scorer = DecisionScorer()

    result = scorer.score_candidates(
        candidates=make_candidates(),
        simulations=make_simulations(),
        stress_tests=make_stress_tests(),
    )

    for score in result.scores:
        components = score.components

        assert 0.0 <= components.target_flight_benefit <= 1.0
        assert 0.0 <= components.network_resilience <= 1.0
        assert 0.0 <= components.network_impact_score <= 1.0
        assert 0.0 <= components.fuel_safety_margin <= 1.0
        assert 0.0 <= components.future_robustness <= 1.0
        assert 0.0 <= score.score <= 1.0


def test_stress_survival_is_future_robustness():
    scorer = DecisionScorer()

    result = scorer.score_candidates(
        candidates=make_candidates(),
        simulations=make_simulations(),
        stress_tests=make_stress_tests(),
    )

    score_map = {
        item.candidate_id: item
        for item in result.scores
    }

    assert (
        score_map["ALT-B"]
        .components
        .future_robustness
        == 0.6
    )

    assert (
        score_map["ALT-C"]
        .components
        .future_robustness
        == 0.8
    )

    assert (
        score_map["ALT-D"]
        .components
        .future_robustness
        == 1.0
    )


def test_network_improvement_increases_network_score():
    scorer = DecisionScorer()

    bad = scorer.score_candidate(
        {
            "id": "BAD",
            "feasible": True,
            "target_delay_min": 5,
        },
        {
            "candidate_id": "BAD",
            "network_delay_delta_min": 10,
            "peak_sector_utilization": 0.95,
        },
    )

    good = scorer.score_candidate(
        {
            "id": "GOOD",
            "feasible": True,
            "target_delay_min": 5,
        },
        {
            "candidate_id": "GOOD",
            "network_delay_delta_min": -10,
            "peak_sector_utilization": 0.80,
        },
    )

    assert (
        good.components.network_impact_score
        > bad.components.network_impact_score
    )


def test_fuel_margin_increases_fuel_component():
    scorer = DecisionScorer()

    low = scorer.score_candidate(
        {
            "id": "LOW",
            "feasible": True,
            "target_delay_min": 5,
            "fuel_margin_kg": 100,
        }
    )

    high = scorer.score_candidate(
        {
            "id": "HIGH",
            "feasible": True,
            "target_delay_min": 5,
            "fuel_margin_kg": 600,
        }
    )

    assert (
        high.components.fuel_safety_margin
        > low.components.fuel_safety_margin
    )


def test_second_intervention_probability_uses_stress_result():
    scorer = DecisionScorer()

    score = scorer.score_candidate(
        {
            "id": "ALT-D",
            "feasible": True,
            "target_delay_min": 8,
            "resilience": 0.91,
        },
        {
            "candidate_id": "ALT-D",
            "network_delay_delta_min": -14,
        },
        {
            "candidate_id": "ALT-D",
            "scenarios_passed": 5,
            "scenarios_total": 5,
        },
    )

    assert score.second_intervention_probability == 0.0


def test_missing_data_degrades_honestly_instead_of_failing():
    scorer = DecisionScorer()

    score = scorer.score_candidate(
        {
            "id": "PARTIAL",
            "feasible": True,
        }
    )

    assert score.candidate_id == "PARTIAL"
    assert 0.0 <= score.score <= 1.0
    assert score.components.future_robustness == 0.5
    assert score.components.fuel_safety_margin == 0.5


def test_scoring_is_deterministic():
    scorer = DecisionScorer()

    first = scorer.score_candidates(
        make_candidates(),
        make_simulations(),
        make_stress_tests(),
    )

    second = scorer.score_candidates(
        make_candidates(),
        make_simulations(),
        make_stress_tests(),
    )

    assert first.model_dump() == second.model_dump()