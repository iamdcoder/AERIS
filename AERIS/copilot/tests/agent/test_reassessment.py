from copilot.agent.reassessment import CandidateReassessor


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
            "fuel_margin_kg": 610,
            "resilience": 0.91,
            "local_score": 0.82,
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


def test_rejection_causes_reranking():
    reassessor = CandidateReassessor()

    result = reassessor.reassess(
        rejected_candidate_id="ALT-D",
        rejection_reason=(
            "Dispatcher wants a lower target delay."
        ),
        candidates=candidates(),
        simulations=simulations(),
        stress_tests=stress_tests(),
    )

    assert result.rejection_reason == (
        "Dispatcher wants a lower target delay."
    )

    assert "ALT-D" in (
        result.excluded_candidate_ids
    )

    assert "ALT-D" not in (
        result.remaining_candidate_ids
    )

    assert result.reranking_performed is True
    assert result.requires_new_approval is True

    assert result.new_recommended_candidate_id in {
        "ALT-B",
        "ALT-C",
    }


def test_rejected_candidate_cannot_become_new_recommendation():
    reassessor = CandidateReassessor()

    result = reassessor.reassess(
        rejected_candidate_id="ALT-D",
        rejection_reason="Try another option.",
        candidates=candidates(),
        simulations=simulations(),
        stress_tests=stress_tests(),
    )

    assert (
        result.new_recommended_candidate_id
        != "ALT-D"
    )


def test_previous_rejections_are_preserved():
    reassessor = CandidateReassessor()

    result = reassessor.reassess(
        rejected_candidate_id="ALT-D",
        rejection_reason="First rejection.",
        candidates=candidates(),
        simulations=simulations(),
        stress_tests=stress_tests(),
        previously_rejected_ids=["ALT-B"],
    )

    assert set(
        result.excluded_candidate_ids
    ) == {
        "ALT-B",
        "ALT-D",
    }

    assert (
        result.remaining_candidate_ids
        == ["ALT-C"]
    )

    assert (
        result.new_recommended_candidate_id
        == "ALT-C"
    )


def test_all_rejected_means_no_new_recommendation():
    reassessor = CandidateReassessor()

    result = reassessor.reassess(
        rejected_candidate_id="ALT-D",
        rejection_reason="Not acceptable.",
        candidates=[
            {
                "id": "ALT-D",
                "feasible": True,
            }
        ],
    )

    assert result.remaining_candidate_ids == []
    assert result.new_recommended_candidate_id is None
    assert result.requires_new_approval is False
    assert result.reranking_performed is False


def test_reassessment_requires_reason():
    reassessor = CandidateReassessor()

    try:
        reassessor.reassess(
            rejected_candidate_id="ALT-D",
            rejection_reason="   ",
            candidates=candidates(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError for empty rejection reason."
        )


def test_reassessment_is_deterministic():
    reassessor = CandidateReassessor()

    first = reassessor.reassess(
        rejected_candidate_id="ALT-D",
        rejection_reason="Try ALT-C.",
        candidates=candidates(),
        simulations=simulations(),
        stress_tests=stress_tests(),
    )

    second = reassessor.reassess(
        rejected_candidate_id="ALT-D",
        rejection_reason="Try ALT-C.",
        candidates=candidates(),
        simulations=simulations(),
        stress_tests=stress_tests(),
    )

    assert first.model_dump() == second.model_dump()