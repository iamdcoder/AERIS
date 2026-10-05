from copilot.agent.orchestrator import (
    AgentOrchestrator,
)
from copilot.engine.client import RealEngineClient
from copilot.mock_engine import MockEngineClient
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
    state = (
        AgentOrchestrator(engine=MockEngineClient())
        .run_mock_preview()
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


def test_agent_creates_investigation_plan():
    state = (
        AgentOrchestrator(engine=MockEngineClient())
        .run_mock_preview()
    )

    assert (
        state.investigation_plan
        is not None
    )

    plan = (
        state.investigation_plan
    )

    assert len(
        plan.questions
    ) >= 4

    tool_names = {
        question.tool_name
        for question
        in plan.questions
    }

    assert (
        "get_weather_state"
        in tool_names
    )

    assert (
        "get_airport_state"
        in tool_names
    )

    assert (
        "get_sector_state"
        in tool_names
    )

    assert (
        "get_network_metrics"
        in tool_names
    )


def test_investigation_is_complete():
    state = (
        AgentOrchestrator(engine=MockEngineClient())
        .run_mock_preview()
    )

    assert (
        state.investigation_plan
        is not None
    )

    assert (
        state.investigation_plan.completeness
        == 1.0
    )

    assert state.investigation_results

    assert all(
        item["status"]
        == "COMPLETED"
        for item
        in state.investigation_results
    )


def test_diagnosis_contains_causal_graph():
    state = (
        AgentOrchestrator(engine=MockEngineClient())
        .run_mock_preview()
    )

    assert (
        state.diagnosis
        is not None
    )

    diagnosis = state.diagnosis

    assert diagnosis.urgency == "HIGH"

    assert (
        diagnosis.evidence_completeness
        == 1.0
    )

    assert diagnosis.causal_chain

    assert (
        len(
            diagnosis.causal_graph.nodes
        )
        >= 3
    )

    assert (
        len(
            diagnosis.causal_graph.edges
        )
        >= 2
    )


def test_orchestrator_uses_registered_tools():
    state = (
        AgentOrchestrator(engine=MockEngineClient())
        .run_mock_preview()
    )

    tool_events = [
        event
        for event in state.events
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
        "get_weather_state",
        "get_airport_state",
        "get_sector_state",
        "get_network_metrics",
        "generate_alternatives",
        "validate_candidate",
        "simulate_network_impact",
        "stress_test_candidate",
    }.issubset(
        tool_names
    )


def test_orchestrator_uses_injected_engine_interface():
    orchestrator = (
        AgentOrchestrator(engine=MockEngineClient())
    )

    assert isinstance(orchestrator.engine, MockEngineClient)


def test_default_orchestrator_uses_real_engine_client():
    orchestrator = AgentOrchestrator()
    assert isinstance(orchestrator.engine, RealEngineClient)


def test_tool_calls_are_visible_as_events():
    state = (
        AgentOrchestrator(engine=MockEngineClient())
        .run_mock_preview()
    )

    calls = [
        event
        for event in state.events
        if event.event_type
        == "TOOL_CALL"
    ]

    results = [
        event
        for event in state.events
        if event.event_type
        == "TOOL_RESULT"
    ]

    assert calls
    assert results

    assert len(calls) == len(
        results
    )