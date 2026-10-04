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