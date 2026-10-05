#!/usr/bin/env python3
"""AERIS — deterministic agentic flagship proof.

This runner exercises the same FastAPI endpoints used by the command center
for the flagship scenario. It proves the observable agent loop, the local-vs-
network reversal, the deterministic critic, the human approval gate, execution,
post-action verification, and the rejection/reassessment path.

Usage from repository root:
    PYTHONPATH=backend python scripts/run_agent_flagship.py
"""
from __future__ import annotations

import os
import sys
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_REPO_ROOT, "backend")
for _path in (_REPO_ROOT, _BACKEND):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fastapi.testclient import TestClient  # noqa: E402
from app.api.app import app  # noqa: E402

SCENARIO_ID = "mumbai_weather_crisis_v2"
TARGET_FLIGHT = "F102"
DECISION_TIME_MIN = 19


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _post(client: TestClient, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=payload)
    _assert(response.status_code == 200, f"{path} failed: {response.status_code} {response.text}")
    return response.json()


def main() -> int:
    client = TestClient(app)

    _post(client, "/copilot/reset", {})
    run_id = "AGENT-FLAGSHIP-001"
    state = _post(
        client,
        "/copilot/investigate",
        {
            "run_id": run_id,
            "scenario_id": SCENARIO_ID,
            "target_flight_id": TARGET_FLIGHT,
            "decision_time_min": DECISION_TIME_MIN,
        },
    )

    recommendation = state.get("recommendation") or {}
    ranking_events = [
        event
        for event in state.get("events", [])
        if event.get("event_type") == "ENGINE_RANKING_READY"
    ]
    critic = state.get("critic_result") or {}

    local_vs_global_flip = bool(
        (ranking_events[-1].get("data") or {}).get("local_vs_global_flip")
    ) if ranking_events else False

    print("\n========================================================")
    print("  AERIS — AGENTIC FLAGSHIP PROOF")
    print(f"  Scenario : {SCENARIO_ID}")
    print(f"  Target   : {TARGET_FLIGHT}")
    print("========================================================")
    print(f"  Stage                 : {state.get('stage')}")
    print(f"  Preliminary leader    : {next((e.get('candidate_id') for e in state.get('events', []) if e.get('event_type') == 'PRELIMINARY_LEADER'), 'UNKNOWN')}")
    print(f"  Network leader        : {(ranking_events[-1].get('candidate_id') if ranking_events else 'UNKNOWN')}")
    print(f"  Local → network flip  : {'YES' if local_vs_global_flip else 'NO'}")
    print(f"  Critic challenged     : {critic.get('challenged')} ({critic.get('candidate_id')})")
    print(f"  Critic replacement    : {critic.get('finding', '')}")
    print(f"  Recommendation        : {recommendation.get('candidate_id')}")
    print(f"  Human approval        : {state.get('approval', {}).get('required')}")

    _assert(state.get("stage") == "HUMAN_APPROVAL", "Agent did not stop at human approval.")
    _assert(recommendation.get("candidate_id") == "ALT-D", "Flagship agent recommendation is not ALT-D.")
    _assert(local_vs_global_flip, "Flagship did not demonstrate the local-vs-network reversal.")
    _assert(critic.get("challenged") is True, "Critic did not challenge the preliminary local leader.")
    _assert(critic.get("candidate_id") == "ALT-A", "Critic did not review the local leader ALT-A.")
    _assert("ALT-D" in str(critic.get("finding", "")), "Critic did not identify ALT-D as the stronger surviving option.")
    _assert(state.get("approval", {}).get("required") is True, "Human approval gate is not required.")

    approved = _post(
        client,
        "/copilot/approve",
        {
            "run_id": run_id,
            "decided_by": "demo_dispatcher",
        },
    )
    verification = approved.get("verification_result") or {}
    print(f"  After approval         : {approved.get('stage')} / {approved.get('status')}")
    print(f"  Verification           : {verification.get('status')}")

    _assert(approved.get("stage") == "COMPLETE", "Approved flagship did not complete.")
    _assert(verification.get("status") == "VERIFIED", "Approved flagship did not verify.")

    # Prove the meaningful rejection/reassessment path on a fresh deterministic run.
    _post(client, "/copilot/reset", {})
    rejection_run_id = "AGENT-FLAGSHIP-REJECT-001"
    rejected = _post(
        client,
        "/copilot/investigate",
        {
            "run_id": rejection_run_id,
            "scenario_id": SCENARIO_ID,
            "target_flight_id": TARGET_FLIGHT,
            "decision_time_min": DECISION_TIME_MIN,
        },
    )
    rejected_id = (rejected.get("recommendation") or {}).get("candidate_id")
    reassessed = _post(
        client,
        "/copilot/reject",
        {
            "run_id": rejection_run_id,
            "reason": "Prefer a different operational trade-off.",
            "decided_by": "demo_dispatcher",
        },
    )
    new_id = (reassessed.get("recommendation") or {}).get("candidate_id")

    print(f"  Rejection path         : {rejected_id} → {new_id}")
    print(f"  Reassessment stage     : {reassessed.get('stage')}")

    _assert(reassessed.get("stage") == "HUMAN_APPROVAL", "Reassessment did not return to human approval.")
    _assert(reassessed.get("status") == "WAITING_HUMAN", "Reassessment did not remain blocked for human review.")
    _assert(new_id and new_id != rejected_id, "Reassessment did not produce a new recommendation.")

    print("\n  AGENTIC FLAGSHIP RESULT: SUCCESS")
    print("  Agent loop, critic, approval, verification and rejection path all passed.")
    print("========================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
