from copilot.agent.orchestrator import AgentOrchestrator
from copilot.engine.client import RealEngineClient


def test_real_orchestrator_uses_authoritative_engine_evidence():
    engine = RealEngineClient()
    engine.reset_engine()
    engine.advance_simulation(19)

    orchestrator = AgentOrchestrator(
        engine_client=engine
    )

    state = orchestrator.run_mock_preview(
        target_flight_id="F102"
    )

    assert state.stage.value == (
        "HUMAN_APPROVAL"
    )

    assert state.recommendation is not None

    assert (
        state.recommendation.candidate_id
        == "ALT-D"
    )

    by_id = {
        candidate["candidate_id"]: candidate
        for candidate in state.candidates
    }

    assert (
        by_id["ALT-A"]["decision_score"]
        == 0.131
    )

    assert (
        by_id["ALT-A"]["target_delay_min"]
        == 0.03
    )

    assert (
        by_id["ALT-A"]["network_delay_delta_min"]
        == 22.03
    )

    assert (
        by_id["ALT-A"]["stress_survival"]
        == {
            "passed": 0,
            "total": 5,
        }
    )

    assert (
        by_id["ALT-D"]["decision_score"]
        == 0.36
    )

    assert (
        by_id["ALT-D"]["target_delay_min"]
        == 4.49
    )

    assert (
        by_id["ALT-D"]["network_delay_delta_min"]
        == 12.49
    )

    assert (
        by_id["ALT-D"]["affected_flights"]
        == 3
    )

    assert (
        by_id["ALT-D"]["stress_survival"]
        == {
            "passed": 4,
            "total": 5,
        }
    )

    assert (
        orchestrator._ranking_summary
        is not None
    )

    assert (
        orchestrator._ranking_summary
        .recommended_candidate_id
        == "ALT-D"
    )

    assert (
        orchestrator._ranking_summary
        .local_vs_global_flip
        is True
    )

def test_approval_gate_recovers_if_controller_state_is_recreated():
    engine = RealEngineClient()
    engine.reset_engine()
    engine.advance_simulation(19)

    orchestrator = AgentOrchestrator(
        engine_client=engine
    )

    state = orchestrator.run_mock_preview(
        run_id="RECOVERY-APPROVAL-001",
        target_flight_id="F102",
    )

    assert state.approval.decision == "PENDING"
    assert orchestrator.approval_controller.is_pending is True

    # Simulate a transient in-memory controller reset while the authoritative
    # AgentState still says that human approval is pending.
    orchestrator.approval_controller.clear()

    approved = orchestrator.approve_current_recommendation(
        decided_by="demo_dispatcher"
    )

    assert approved.approval.decision == "APPROVED"
    assert approved.status.value == "COMPLETED"
    assert approved.verification_result is not None


def test_rejection_gate_recovers_if_controller_state_is_recreated():
    engine = RealEngineClient()
    engine.reset_engine()
    engine.advance_simulation(19)

    orchestrator = AgentOrchestrator(
        engine_client=engine
    )

    state = orchestrator.run_mock_preview(
        run_id="RECOVERY-REJECT-001",
        target_flight_id="F102",
    )

    assert state.approval.decision == "PENDING"

    orchestrator.approval_controller.clear()

    rejected = orchestrator.reject_current_recommendation(
        reason="Dispatcher wants reassessment.",
        decided_by="demo_dispatcher",
    )

    assert rejected.approval.decision == "REJECTED"
    assert rejected.stage.value == "DEGRADED"
    assert rejected.recommendation is None
