from copilot.agent.ranker import DecisionRanker


def candidates():
    return [
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
            "resilience": 0.91,
            "fuel_margin_kg": 610,
            "local_score": 0.82,
        },
        {
            "id": "ALT-A",
            "feasible": False,
            "target_delay_min": 2,
            "local_score": 0.98,
        },
    ]


def simulations():
    return [
        {
            "candidate_id": "ALT-B",
            "network_delay_delta_min": 2,
            "peak_sector_utilization": 0.94,
            "affected_flights": 4,
        },
        {
            "candidate_id": "ALT-C",
            "network_delay_delta_min": -3,
            "peak_sector_utilization": 0.86,
            "affected_flights": 3,
        },
        {
            "candidate_id": "ALT-D",
            "network_delay_delta_min": -14,
            "peak_sector_utilization": 0.82,
            "affected_flights": 1,
        },
    ]


def stress_tests():
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


def test_ranker_selects_alt_d():
    ranker = DecisionRanker()

    score_result, summary = ranker.rank(
        candidates(),
        simulations(),
        stress_tests(),
    )

    assert summary.recommended_candidate_id == "ALT-D"

    assert (
        score_result.recommended_candidate_id
        == "ALT-D"
    )


def test_ranker_places_infeasible_candidates_after_feasible():
    ranker = DecisionRanker()

    _, summary = ranker.rank(
        candidates(),
        simulations(),
        stress_tests(),
    )

    assert summary.ranked_candidates[0].candidate_id == "ALT-D"
    assert summary.ranked_candidates[0].feasible is True

    assert summary.ranked_candidates[-1].candidate_id == "ALT-A"
    assert summary.ranked_candidates[-1].feasible is False


def test_rank_numbers_are_sequential():
    ranker = DecisionRanker()

    _, summary = ranker.rank(
        candidates(),
        simulations(),
        stress_tests(),
    )

    ranks = [
        item.rank
        for item in summary.ranked_candidates
    ]

    assert ranks == [1, 2, 3, 4]


def test_score_gap_is_computed():
    ranker = DecisionRanker()

    _, summary = ranker.rank(
        candidates(),
        simulations(),
        stress_tests(),
    )

    assert summary.score_gap >= 0.0


def test_local_global_flip_is_detected():
    ranker = DecisionRanker()

    _, summary = ranker.rank(
        candidates(),
        simulations(),
        stress_tests(),
    )

    assert summary.local_vs_global_flip is True


def test_rationale_mentions_network_level_tradeoff():
    ranker = DecisionRanker()

    _, summary = ranker.rank(
        candidates(),
        simulations(),
        stress_tests(),
    )

    assert (
        "network-level winner"
        in summary.rationale
    )


def test_no_feasible_candidates_returns_no_recommendation():
    ranker = DecisionRanker()

    blocked = [
        {
            "id": "ALT-A",
            "feasible": False,
            "rejection_reasons": [
                "Sector overload"
            ],
        },
        {
            "id": "ALT-E",
            "feasible": False,
            "rejection_reasons": [
                "Fuel insufficiency"
            ],
        },
    ]

    _, summary = ranker.rank(blocked)

    assert summary.recommended_candidate_id is None

    assert (
        "No feasible candidate"
        in summary.rationale
    )