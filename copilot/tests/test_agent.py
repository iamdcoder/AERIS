from copilot.agent.orchestrator import (
    AgentOrchestrator,
)
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

    assert (
        state.stage
        == AgentStage.DIAGNOSE
    )

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
    orchestrator = AgentOrchestrator()

    state = (
        orchestrator.run_mock_preview()
    )

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

    assert (
        state.recommendation
        is not None
    )

    assert (
        state.recommendation.candidate_id
        == "ALT-D"
    )

    assert (
        state.critic_result
        is not None
    )

    assert (
        state.critic_result.candidate_id
        == "ALT-B"
    )

    assert (
        state.critic_result.challenged
        is True
    )


def test_orchestrator_uses_registered_tools():
    orchestrator = (
        AgentOrchestrator()
    )

    state = (
        orchestrator.run_mock_preview()
    )

    tool_events = [
        event
        for event
        in state.events
        if event.event_type
        == "TOOL_RESULT"
    ]

    tool_names = {
        event.tool_name
        for event
        in tool_events
    }

    assert {
        "get_airspace_state",
        "get_disruptions",
        "get_target_flight",
        "generate_alternatives",
        "validate_candidate",
        "simulate_network_impact",
        "stress_test_candidate",
    }.issubset(
        tool_names
    )