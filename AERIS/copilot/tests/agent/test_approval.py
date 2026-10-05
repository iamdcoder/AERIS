import pytest

from copilot.agent.approval import (
    ApprovalController,
    ApprovalDecision,
)


def test_request_creates_pending_human_gate():
    controller = ApprovalController()

    request = controller.request(
        recommendation_id="REC-001",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation="ALT-D has strongest network resilience.",
    )

    assert request.candidate_id == "ALT-D"
    assert request.target_flight_id == "F102"

    assert controller.is_pending is True
    assert controller.is_approved is False
    assert controller.is_rejected is False

    assert (
        controller.current_record.decision
        == ApprovalDecision.PENDING
    )


def test_approval_requires_pending_request():
    controller = ApprovalController()

    with pytest.raises(RuntimeError):
        controller.approve()


def test_rejection_requires_pending_request():
    controller = ApprovalController()

    with pytest.raises(RuntimeError):
        controller.reject(
            "I prefer another route."
        )


def test_approve_records_human_decision():
    controller = ApprovalController()

    controller.request(
        recommendation_id="REC-001",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation="Strongest resilient option.",
    )

    record = controller.approve(
        decided_by="dispatcher_1"
    )

    assert record.decision == ApprovalDecision.APPROVED
    assert record.candidate_id == "ALT-D"
    assert record.decided_by == "dispatcher_1"
    assert record.reason is None

    assert controller.is_approved is True
    assert controller.is_pending is False


def test_reject_requires_non_empty_reason():
    controller = ApprovalController()

    controller.request(
        recommendation_id="REC-002",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation="Strongest resilient option.",
    )

    with pytest.raises(ValueError):
        controller.reject("   ")


def test_rejection_records_reason():
    controller = ApprovalController()

    controller.request(
        recommendation_id="REC-002",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation="Strongest resilient option.",
    )

    record = controller.reject(
        reason="Dispatcher prefers lower target delay.",
        decided_by="dispatcher_1",
    )

    assert record.decision == ApprovalDecision.REJECTED
    assert (
        record.reason
        == "Dispatcher prefers lower target delay."
    )
    assert record.decided_by == "dispatcher_1"

    assert controller.is_rejected is True


def test_approval_history_is_preserved():
    controller = ApprovalController()

    controller.request(
        recommendation_id="REC-001",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation="First recommendation.",
    )

    controller.reject(
        "Try a lower-delay candidate."
    )

    controller.reset_for_reassessment()

    controller.request(
        recommendation_id="REC-002",
        candidate_id="ALT-C",
        target_flight_id="F102",
        explanation="Second recommendation.",
    )

    controller.approve()

    history = controller.history

    assert len(history) == 2

    assert (
        history[0].candidate_id
        == "ALT-D"
    )

    assert (
        history[0].decision
        == ApprovalDecision.REJECTED
    )

    assert (
        history[1].candidate_id
        == "ALT-C"
    )

    assert (
        history[1].decision
        == ApprovalDecision.APPROVED
    )


def test_only_one_pending_request_can_exist():
    controller = ApprovalController()

    controller.request(
        recommendation_id="REC-001",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation="First.",
    )

    with pytest.raises(RuntimeError):
        controller.request(
            recommendation_id="REC-002",
            candidate_id="ALT-C",
            target_flight_id="F102",
            explanation="Second.",
        )


def test_reset_clears_active_gate():
    controller = ApprovalController()

    controller.request(
        recommendation_id="REC-001",
        candidate_id="ALT-D",
        target_flight_id="F102",
        explanation="Recommendation.",
    )

    controller.reset_for_reassessment()

    assert controller.active_request is None
    assert controller.current_record is None
    assert controller.is_pending is False