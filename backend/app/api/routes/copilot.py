"""AERIS copilot API routes."""
from __future__ import annotations

from threading import RLock

from fastapi import APIRouter, HTTPException

from ..schemas.requests import (
    CopilotApprovalRequest,
    CopilotRejectionRequest,
    CopilotRequest,
)

router = APIRouter()

_RUNS = {}
_RUNS_LOCK = RLock()


def _store_run(
    run_id: str,
    orchestrator,
) -> None:
    with _RUNS_LOCK:
        _RUNS[run_id] = orchestrator


def _get_run(
    run_id: str,
):
    with _RUNS_LOCK:
        return _RUNS.get(
            run_id
        )


def _run_orchestrator(
    body: CopilotRequest,
    *,
    use_gemini: bool,
) -> dict:
    try:
        from copilot.agent import (
            AgentOrchestrator,
        )
        from copilot.engine.client import (
            RealEngineClient,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Copilot layer unavailable: {exc}"
            ),
        ) from exc

    client = RealEngineClient()

    orchestrator = AgentOrchestrator(
        engine_client=client
    )

    kwargs = {
        "run_id": body.run_id,
        "scenario_id": body.scenario_id,
        "target_flight_id": body.target_flight_id,
    }

    if use_gemini:
        agent_state = (
            orchestrator.run_hybrid_preview(
                **kwargs
            )
        )
    else:
        agent_state = (
            orchestrator.run_mock_preview(
                **kwargs
            )
        )

    _store_run(
        body.run_id,
        orchestrator,
    )

    return agent_state.model_dump()


@router.post(
    "/copilot/investigate",
    summary="Run deterministic copilot investigation",
)
def post_investigate(
    body: CopilotRequest,
):
    try:
        return _run_orchestrator(
            body,
            use_gemini=False,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post(
    "/copilot/recommend",
    summary=(
        "Run hybrid investigation and prepare recommendation"
    ),
)
def post_recommend(
    body: CopilotRequest,
):
    try:
        return _run_orchestrator(
            body,
            use_gemini=True,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post(
    "/copilot/approve",
    summary="Approve the current AERIS recommendation",
)
def post_approve(
    body: CopilotApprovalRequest,
):
    orchestrator = _get_run(
        body.run_id
    )

    if orchestrator is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"AERIS run {body.run_id!r} "
                "was not found."
            ),
        )

    try:
        state = (
            orchestrator.approve_current_recommendation(
                decided_by=body.decided_by
            )
        )

        return state.model_dump()

    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


@router.post(
    "/copilot/reject",
    summary="Reject and reassess the current recommendation",
)
def post_reject(
    body: CopilotRejectionRequest,
):
    orchestrator = _get_run(
        body.run_id
    )

    if orchestrator is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"AERIS run {body.run_id!r} "
                "was not found."
            ),
        )

    try:
        state = (
            orchestrator.reject_current_recommendation(
                reason=body.reason,
                decided_by=body.decided_by,
            )
        )

        return state.model_dump()

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


@router.post(
    "/copilot/reset",
    summary="Reset the deterministic scenario for a new run",
)
def post_reset():
    try:
        from copilot.engine.client import (
            RealEngineClient,
        )

        client = RealEngineClient()
        client.reset_engine()

        with _RUNS_LOCK:
            _RUNS.clear()

        return {
            "status": "RESET",
            "message": (
                "AERIS deterministic simulation state "
                "was reset to the scenario baseline."
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc