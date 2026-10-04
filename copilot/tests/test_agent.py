from copilot.agent.orchestrator import AgentOrchestrator
from copilot.agent.state import (
    AgentStage,
    RunStatus,
    can_transition,
    new_agent_state,
    transition,
)


def test_valid_state_transition():
    state = new_agent_state(
        "RUN-TEST",
        "scenario",
        "F102",
    )

    transition(
        state,
        AgentStage.DIAGNOSE,
        "begin diagnosis",
    )

    assert state.stage == AgentStage.DIAGNOSE
    assert state.step == 1


def test_invalid_state_transition_is_rejected():
    state = new_agent_state(
        "RUN-TEST",
        "scenario",
        "F102",
    )

    assert (
        can_transition(
            AgentStage.OBSERVE,
            AgentStage.RECOMMEND,
        )
        is False
    )


def test_mock_preview_stops_for_human_approval():
    state = AgentOrchestrator().run_mock_preview()

    assert (
        state.status
        == RunStatus.WAITING_HUMAN
    )

    assert (
        state.stage
        == AgentStage.HUMAN_APPROVAL
    )

    assert (
        state.leading_candidate_id
        == "ALT-D"
    )

    assert state.recommendation is not None

    assert (
        state.recommendation.candidate_id
        == "ALT-D"
    )

    assert (
        state.critic_result is not None
    )

    assert (
        state.critic_result.candidate_id
        == "ALT-B"
    )

    assert (
        state.critic_result.challenged
        is True
    )

    rejected = {
        item["candidate_id"]
        for item
        in state.recommendation.rejected_candidates
    }

    assert rejected == {
        "ALT-A",
        "ALT-E",
    }