"""Decision endpoints — generate, validate, simulate, stress-test, score, apply, verify."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...engine import public as engine
from ..schemas.requests import (
    AlternativesRequest,
    CandidateRequest,
    DecisionScoreRequest,
    ApplyRequest,
    VerifyRequest,
)

router = APIRouter()


@router.post("/alternatives", summary="Generate alternative candidate routes for a flight")
def post_alternatives(body: AlternativesRequest):
    """Generate deterministic intervention candidates for the specified flight."""
    try:
        candidates = engine.generate_alternatives(body.flight_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"flight_id": body.flight_id, "candidates": candidates}


@router.post("/validate", summary="Validate a candidate against all hard constraints")
def post_validate(body: CandidateRequest):
    """Run constraint validation on the supplied candidate. Does not apply it."""
    try:
        result = engine.validate_candidate(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.post("/simulate", summary="Run 20-minute network simulation for a candidate")
def post_simulate(body: CandidateRequest):
    """Simulate the network-level impact of applying this candidate."""
    try:
        result = engine.simulate_candidate(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.post("/stress-test", summary="Run the five-scenario stress test for a candidate")
def post_stress_test(body: CandidateRequest):
    """Stress-test the candidate across five future scenarios and return a survivability report."""
    try:
        report = engine.stress_test_candidate(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return report


@router.post("/decision-score", summary="Score and rank a list of candidates")
def post_decision_score(body: DecisionScoreRequest):
    """Validate, simulate, stress-test, and score all supplied candidates; return ranked results."""
    try:
        scored = engine.score_candidates(body.candidates)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"scored_candidates": scored}


@router.post("/apply", summary="Apply an approved candidate intervention")
def post_apply(body: ApplyRequest):
    """Apply a previously generated candidate to the live engine state.

    The `approved` flag must be `true` — this acts as an explicit human-approval gate.
    """
    if not body.approved:
        raise HTTPException(
            status_code=403,
            detail="Human approval required: set 'approved: true' to apply.",
        )
    try:
        result = engine.apply_intervention(body.candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.post("/verify", summary="Verify the currently applied intervention")
def post_verify(body: VerifyRequest):
    """Compare the live state against the baseline to verify the intervention is holding."""
    try:
        result = engine.verify_state(body.candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result
