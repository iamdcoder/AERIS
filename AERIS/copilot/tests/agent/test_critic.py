from copilot.agent.critic import DecisionCritic
from copilot.agent.ranker import DecisionRanker
from copilot.agent.scoring import DecisionScorer


def make_data():
    candidates = [
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
    ]

    simulations = [
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
            "new_conflicts": 0,
            "downstream_risk": "very low",
        },
    ]

    stress_tests = [
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

    return candidates, simulations, stress_tests


def test_critic_validates_robust_alt_d():
    candidates, simulations, stress_tests = make_data()

    ranker = DecisionRanker()

    score_result, ranking = ranker.rank(
        candidates,
        simulations,
        stress_tests,
    )

    leader = next(
        item
        for item in score_result.scores
        if item.candidate_id == ranking.recommended_candidate_id
    )

    critic = DecisionCritic()

    result = critic.review(
        leader=leader,
        ranking=ranking,
        stress_test={
            "candidate_id": "ALT-D",
            "scenarios_passed": 5,
            "scenarios_total": 5,
        },
        simulation={
            "candidate_id": "ALT-D",
            "network_delay_delta_min": -14,
            "peak_sector_utilization": 0.82,
            "new_conflicts": 0,
            "downstream_risk": "very low",
        },
    )

    assert result.candidate_id == "ALT-D"
    assert result.challenged is False
    assert result.should_reconsider is False
    assert result.challenge_severity == "NONE"
    assert result.replacement_candidate_id is None

    assert (
        "No material failure condition"
        in result.summary
    )


def test_critic_detects_fragile_candidate():
    candidates, simulations, stress_tests = make_data()

    scorer = DecisionScorer()

    leader = scorer.score_candidate(
        candidates[0],
        simulations[0],
        stress_tests[0],
    )

    ranker = DecisionRanker()

    _, ranking = ranker.rank(
        candidates,
        simulations,
        stress_tests,
    )

    result = DecisionCritic().review(
        leader=leader,
        ranking=ranking,
        stress_test={
            "candidate_id": "ALT-B",
            "scenarios_passed": 2,
            "scenarios_total": 5,
        },
        simulation={
            "candidate_id": "ALT-B",
            "network_delay_delta_min": 2,
            "peak_sector_utilization": 1.08,
            "new_conflicts": 0,
        },
    )

    assert result.challenged is True
    assert result.should_reconsider is True

    categories = {
        finding.category
        for finding in result.findings
    }

    assert "FUTURE_ROBUSTNESS" in categories
    assert "SECTOR_CAPACITY" in categories


def test_critic_detects_new_conflict():
    candidates, simulations, stress_tests = make_data()

    scorer = DecisionScorer()

    leader = scorer.score_candidate(
        candidates[2],
        simulations[2],
        stress_tests[2],
    )

    ranker = DecisionRanker()

    _, ranking = ranker.rank(
        candidates,
        simulations,
        stress_tests,
    )

    result = DecisionCritic().review(
        leader=leader,
        ranking=ranking,
        stress_test=stress_tests[2],
        simulation={
            "candidate_id": "ALT-D",
            "peak_sector_utilization": 0.82,
            "new_conflicts": 2,
        },
    )

    assert result.challenged is True
    assert result.should_reconsider is True
    assert result.challenge_severity == "CRITICAL"

    assert any(
        finding.category == "CONFLICT_RISK"
        for finding in result.findings
    )


def test_critic_checks_all_required_failure_modes():
    candidates, simulations, stress_tests = make_data()

    ranker = DecisionRanker()

    score_result, ranking = ranker.rank(
        candidates,
        simulations,
        stress_tests,
    )

    leader = score_result.scores[0]

    result = DecisionCritic().review(
        leader=leader,
        ranking=ranking,
    )

    assert result.failure_modes_checked == [
        "WORSENING_WEATHER",
        "REDUCED_SECTOR_CAPACITY",
        "INCREASED_TRAFFIC",
        "NEW_RESTRICTION",
        "DOWNSTREAM_AIRPORT_DEGRADATION",
    ]


def test_critic_is_deterministic():
    candidates, simulations, stress_tests = make_data()

    ranker = DecisionRanker()

    score_result, ranking = ranker.rank(
        candidates,
        simulations,
        stress_tests,
    )

    leader = next(
        item
        for item in score_result.scores
        if item.candidate_id == ranking.recommended_candidate_id
    )

    critic = DecisionCritic()

    first = critic.review(
        leader,
        ranking,
        stress_tests[2],
        simulations[2],
    )

    second = critic.review(
        leader,
        ranking,
        stress_tests[2],
        simulations[2],
    )

    assert first.model_dump() == second.model_dump()