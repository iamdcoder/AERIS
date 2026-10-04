from copilot.agent.critic import CriticResult, DecisionCritic
from copilot.agent.ranker import DecisionRanker
from copilot.agent.synthesizer import DecisionSynthesizer


def build_pipeline():
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

    ranker = DecisionRanker()

    score_result, ranking = ranker.rank(
        candidates,
        simulations,
        stress_tests,
    )

    return (
        score_result,
        ranking,
        simulations,
        stress_tests,
    )


def test_synthesizer_recommends_alt_d():
    (
        score_result,
        ranking,
        simulations,
        stress_tests,
    ) = build_pipeline()

    leader = next(
        item
        for item in score_result.scores
        if item.candidate_id
        == ranking.recommended_candidate_id
    )

    critic_result = DecisionCritic().review(
        leader=leader,
        ranking=ranking,
        stress_test=stress_tests[2],
        simulation=simulations[2],
    )

    recommendation = DecisionSynthesizer().synthesize(
        ranking=ranking,
        score_result=score_result,
        critic_result=critic_result,
        target_flight_id="F102",
    )

    assert recommendation.candidate_id == "ALT-D"
    assert recommendation.decision == "RECOMMEND"
    assert recommendation.requires_human_approval is True
    assert recommendation.target_flight_id == "F102"

    assert recommendation.critic_challenged is False
    assert recommendation.future_robustness == 1.0


def test_synthesizer_preserves_human_approval_gate():
    (
        score_result,
        ranking,
        simulations,
        stress_tests,
    ) = build_pipeline()

    leader = next(
        item
        for item in score_result.scores
        if item.candidate_id
        == ranking.recommended_candidate_id
    )

    critic_result = DecisionCritic().review(
        leader=leader,
        ranking=ranking,
        stress_test=stress_tests[2],
        simulation=simulations[2],
    )

    recommendation = DecisionSynthesizer().synthesize(
        ranking,
        score_result,
        critic_result,
        "F102",
    )

    assert recommendation.requires_human_approval is True


def test_synthesizer_has_structured_evidence():
    (
        score_result,
        ranking,
        simulations,
        stress_tests,
    ) = build_pipeline()

    leader = next(
        item
        for item in score_result.scores
        if item.candidate_id
        == ranking.recommended_candidate_id
    )

    critic_result = DecisionCritic().review(
        leader,
        ranking,
        stress_tests[2],
        simulations[2],
    )

    recommendation = DecisionSynthesizer().synthesize(
        ranking,
        score_result,
        critic_result,
        "F102",
    )

    categories = {
        evidence.category
        for evidence in recommendation.evidence
    }

    assert "DECISION_SCORE" in categories
    assert "TARGET_IMPACT" in categories
    assert "NETWORK_IMPACT" in categories
    assert "NETWORK_RESILIENCE" in categories
    assert "FUTURE_ROBUSTNESS" in categories
    assert "REINTERVENTION" in categories


def test_synthesizer_changes_leader_when_critic_finds_replacement():
    (
        score_result,
        ranking,
        simulations,
        stress_tests,
    ) = build_pipeline()

    original_leader = ranking.recommended_candidate_id

    assert original_leader == "ALT-D"

    critic_result = CriticResult(
        candidate_id="ALT-D",
        challenged=True,
        challenge_severity="HIGH",
        findings=[],
        failure_modes_checked=[],
        surviving_checks=[],
        should_reconsider=True,
        replacement_candidate_id="ALT-C",
        summary=(
            "Critic found a significant future risk in ALT-D "
            "and identified ALT-C as the strongest surviving "
            "alternative."
        ),
    )

    recommendation = DecisionSynthesizer().synthesize(
        ranking=ranking,
        score_result=score_result,
        critic_result=critic_result,
        target_flight_id="F102",
    )

    assert recommendation.candidate_id == "ALT-C"
    assert recommendation.critic_challenged is True
    assert recommendation.decision == "RECOMMEND"


def test_synthesizer_returns_no_safe_recommendation():
    (
        score_result,
        ranking,
        simulations,
        stress_tests,
    ) = build_pipeline()

    empty_ranking = ranking.model_copy(
        update={
            "recommended_candidate_id": None,
        }
    )

    critic_result = CriticResult(
        candidate_id="NONE",
        challenged=False,
        challenge_severity="NONE",
        findings=[],
        failure_modes_checked=[],
        surviving_checks=[],
        should_reconsider=False,
        replacement_candidate_id=None,
        summary="No candidate was available.",
    )

    recommendation = DecisionSynthesizer().synthesize(
        ranking=empty_ranking,
        score_result=score_result,
        critic_result=critic_result,
        target_flight_id="F102",
    )

    assert recommendation.candidate_id is None
    assert recommendation.decision == "NO_SAFE_RECOMMENDATION"
    assert recommendation.confidence == 0.0
    assert recommendation.requires_human_approval is True


def test_synthesizer_is_deterministic():
    (
        score_result,
        ranking,
        simulations,
        stress_tests,
    ) = build_pipeline()

    leader = next(
        item
        for item in score_result.scores
        if item.candidate_id
        == ranking.recommended_candidate_id
    )

    critic_result = DecisionCritic().review(
        leader,
        ranking,
        stress_tests[2],
        simulations[2],
    )

    synthesizer = DecisionSynthesizer()

    first = synthesizer.synthesize(
        ranking,
        score_result,
        critic_result,
        "F102",
    )

    second = synthesizer.synthesize(
        ranking,
        score_result,
        critic_result,
        "F102",
    )

    assert first.model_dump() == second.model_dump()