"""Copilot endpoints — AI-orchestrated investigation and recommendation."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas.requests import CopilotRequest

router = APIRouter()


def _run_orchestrator(body: CopilotRequest, *, use_gemini: bool) -> dict:
    """Instantiate the orchestrator and run the appropriate investigation mode."""
    try:
        from copilot.agent import AgentOrchestrator
        from copilot.engine.client import RealEngineClient
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Copilot layer unavailable: {exc}",
        ) from exc

    client = RealEngineClient()
    orchestrator = AgentOrchestrator(engine_client=client)

    kwargs = dict(
        run_id=body.run_id,
        scenario_id=body.scenario_id,
        target_flight_id=body.target_flight_id,
    )

    if use_gemini:
        agent_state = orchestrator.run_hybrid_preview(**kwargs)
    else:
        agent_state = orchestrator.run_mock_preview(**kwargs)

    return agent_state.model_dump()


@router.post("/copilot/investigate", summary="Run deterministic copilot investigation")
def post_investigate(body: CopilotRequest):
    """Run a deterministic (non-LLM) investigation and return the full agent state.

    This is the reproducible, offline-safe path. Use for testing and when Gemini
    is not available.
    """
    try:
        result = _run_orchestrator(body, use_gemini=False)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@router.post("/copilot/recommend", summary="Run hybrid Gemini-backed investigation and recommendation")
def post_recommend(body: CopilotRequest):
    """Run the full Gemini-backed hybrid investigation.

    Falls back to deterministic diagnosis if Gemini is unavailable or evidence is
    insufficient. Both paths converge into the same evaluation/stress-test/critic
    pipeline. Returns a full decision package including recommendation.
    """
    try:
        result = _run_orchestrator(body, use_gemini=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result
