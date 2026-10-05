from copilot.agent.approval import (
    ApprovalController,
    ApprovalDecision,
)
from copilot.agent.decision_lifecycle import (
    DecisionLifecycleController,
)
from copilot.agent.execution import (
    ExecutionStatus,
)
from copilot.agent.verification import (
    VerificationStatus,
)


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
            "new_conflicts": 0,
            "downstream_risk": "medium",
        },
        {
            "candidate_id": "ALT-C",
            "network_delay_delta_min": -3,
            "peak_sector_utilization": 0.86,
            "affected_flights": 3,
            "new_conflicts": 0,
            "downstream_risk": "low",
        },
        {
            "candidate_id": "ALT-D",
            "network_delay_delta_min": -14,
            "peak_sector_utilization": 0.82,
            "affected_flights": 1,
            "new_conflicts": 0,
            "fuel_margin_kg": 610,
            "downstream_risk": "very low",
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


def make_approved_record():
    controller = ApprovalController()

    controller.request(
        recommendation_id="REC-001",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation=(
            "ALT-D has the strongest network resilience."
        ),
    )

    return controller.approve(
        decided_by="dispatcher_1"
    )


def make_rejected_record():
    controller = ApprovalController()

    controller.request(
        recommendation_id="REC-002",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation=(
            "ALT-D is the resilient recommendation."
        ),
    )

    return controller.reject(
        reason=(
            "Dispatcher prefers a lower target-flight delay."
        ),
        decided_by="dispatcher_1",
    )


def test_approved_intervention_executes():
    record = make_approved_record()

    lifecycle = DecisionLifecycleController()

    result = lifecycle.process_approval(
        approval_record=record,
        target_flight_id="F102",
        candidate=candidates()[2],
        simulation=simulations()[2],
    )

    assert result.execution is not None

    assert (
        result.execution.status
        == ExecutionStatus.EXECUTED
    )

    assert (
        result.execution.approval_verified
        is True
    )


def test_approved_alt_d_verifies():
    record = make_approved_record()

    lifecycle = DecisionLifecycleController()

    result = lifecycle.process_approval(
        approval_record=record,
        target_flight_id="F102",
        candidate=candidates()[2],
        simulation=simulations()[2],
    )

    assert result.verification is not None

    assert (
        result.verification.status
        == VerificationStatus.VERIFIED
    )

    assert result.completed is True
    assert result.requires_human_approval is False


def test_pending_approval_blocks_execution():
    controller = ApprovalController()

    controller.request(
        recommendation_id="REC-003",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation="Waiting for dispatcher.",
    )

    record = controller.current_record

    lifecycle = DecisionLifecycleController()

    result = lifecycle.process_approval(
        approval_record=record,
        target_flight_id="F102",
        candidate=candidates()[2],
        simulation=simulations()[2],
    )

    assert result.execution is None
    assert result.completed is False
    assert result.requires_human_approval is True


def test_rejected_intervention_never_executes():
    record = make_rejected_record()

    lifecycle = DecisionLifecycleController()

    result = lifecycle.process_approval(
        approval_record=record,
        target_flight_id="F102",
        candidate=candidates()[2],
        simulation=simulations()[2],
    )

    assert result.execution is None
    assert result.verification is None
    assert result.completed is False


def test_rejection_reassesses_remaining_candidates():
    record = make_rejected_record()

    lifecycle = DecisionLifecycleController()

    result = lifecycle.process_rejection(
        approval_record=record,
        candidates=candidates(),
        simulations=simulations(),
        stress_tests=stress_tests(),
    )

    assert result.reassessment is not None

    reassessment = result.reassessment

    assert "ALT-D" in (
        reassessment.excluded_candidate_ids
    )

    assert (
        "ALT-D"
        not in reassessment.remaining_candidate_ids
    )

    assert (
        reassessment.new_recommended_candidate_id
        in {"ALT-B", "ALT-C"}
    )

    assert result.requires_human_approval is True


def test_all_candidates_rejected_ends_cycle():
    controller = ApprovalController()

    controller.request(
        recommendation_id="REC-004",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation="First option.",
    )

    record = controller.reject(
        "Not acceptable."
    )

    lifecycle = DecisionLifecycleController()

    result = lifecycle.process_rejection(
        approval_record=record,
        candidates=[
            {
                "id": "ALT-D",
                "feasible": True,
            }
        ],
    )

    assert (
        result.reassessment
        .new_recommended_candidate_id
        is None
    )

    assert (
        result.requires_human_approval
        is False
    )


def test_verification_failure_triggers_reassessment():
    record = make_approved_record()

    lifecycle = DecisionLifecycleController()

    result = lifecycle.process_approval(
        approval_record=record,
        target_flight_id="F102",
        candidate=candidates()[2],
        simulation={
            "candidate_id": "ALT-D",
            "network_delay_delta_min": 12,
            "peak_sector_utilization": 1.08,
            "new_conflicts": 2,
            "fuel_margin_kg": -20,
            "downstream_risk": "high",
        },
    )

    assert result.execution is not None
    assert result.verification is not None

    assert (
        result.verification.status
        == VerificationStatus.REASSESSMENT_REQUIRED
    )

    reassessment = (
        lifecycle.reassess_after_verification_failure(
            verification=result.verification,
            candidates=candidates(),
            simulations=simulations(),
            stress_tests=stress_tests(),
        )
    )

    assert reassessment.reranking_performed is True

    assert (
        reassessment.rejected_candidate_id
        == "ALT-D"
    )

    assert (
        reassessment.new_recommended_candidate_id
        in {"ALT-B", "ALT-C"}
    )


def test_alt_d_simulation_verification_checks_expected_conditions():
    record = make_approved_record()

    lifecycle = DecisionLifecycleController()

    result = lifecycle.process_approval(
        approval_record=record,
        target_flight_id="F102",
        candidate=candidates()[2],
        simulation=simulations()[2],
    )

    checks = result.verification.checks

    assert checks["no_new_conflicts"] is True
    assert checks["sector_capacity_safe"] is True
    assert checks["fuel_margin_safe"] is True
    assert checks["downstream_risk_acceptable"] is True
    assert checks["network_not_worsened"] is True


def test_lifecycle_is_deterministic():
    record_1 = make_approved_record()
    record_2 = make_approved_record()

    lifecycle_1 = DecisionLifecycleController()
    lifecycle_2 = DecisionLifecycleController()

    first = lifecycle_1.process_approval(
        approval_record=record_1,
        target_flight_id="F102",
        candidate=candidates()[2],
        simulation=simulations()[2],
    )

    second = lifecycle_2.process_approval(
        approval_record=record_2,
        target_flight_id="F102",
        candidate=candidates()[2],
        simulation=simulations()[2],
    )

    assert first.model_dump() == second.model_dump()


def test_failed_execution_does_not_claim_verified():
    record = make_approved_record()

    class FailingRegistry:
        def invoke(self, tool_name, arguments):
            class Result:
                ok = False
                data = {}
                error_message = (
                    "Execution engine unavailable."
                )

            return Result()

    lifecycle = DecisionLifecycleController()

    result = lifecycle.process_approval(
        approval_record=record,
        target_flight_id="F102",
        candidate=candidates()[2],
        registry=FailingRegistry(),
        simulation=simulations()[2],
    )

    assert result.execution is not None

    assert (
        result.execution.status
        == ExecutionStatus.FAILED
    )

    assert result.verification is None
    assert result.completed is False