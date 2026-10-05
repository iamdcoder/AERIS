from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.routes import copilot as copilot_routes
from app.engine import public


@pytest.fixture()
def client():
    public.reset_engine()

    with copilot_routes._RUNS_LOCK:
        copilot_routes._RUNS.clear()

    test_client = TestClient(
        create_app()
    )

    yield test_client

    public.reset_engine()

    with copilot_routes._RUNS_LOCK:
        copilot_routes._RUNS.clear()


def request_payload(
    run_id: str = "API-TEST-001",
):
    return {
        "run_id": run_id,
        "target_flight_id": "F102",
        "scenario_id": (
            "mumbai_weather_crisis_v2"
        ),
    }


def test_investigate_starts_at_flagship_decision_point(
    client,
):
    response = client.post(
        "/copilot/investigate",
        json=request_payload(),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["stage"] == (
        "HUMAN_APPROVAL"
    )

    assert body["status"] == (
        "WAITING_HUMAN"
    )

    assert (
        body["world_state"]["time_min"]
        == 19
    )

    assert body["scenario_id"] == (
        "mumbai_weather_crisis_v2"
    )

    assert body["target_flight_id"] == (
        "F102"
    )


def test_recommendation_uses_authoritative_engine_evidence(
    client,
):
    response = client.post(
        "/copilot/recommend",
        json=request_payload(
            "API-TEST-002"
        ),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["stage"] == (
        "HUMAN_APPROVAL"
    )

    assert (
        body["recommendation"]
        ["candidate_id"]
        == "ALT-D"
    )

    assert (
        body["leading_candidate_id"]
        == "ALT-D"
    )

    candidates = {
        item["candidate_id"]: item
        for item in body["candidates"]
    }

    assert (
        candidates["ALT-A"]
        ["decision_score"]
        == 0.131
    )

    assert (
        candidates["ALT-A"]
        ["network_delay_delta_min"]
        == 22.03
    )

    assert (
        candidates["ALT-A"]
        ["stress_survival"]
        == {
            "passed": 0,
            "total": 5,
        }
    )

    assert (
        candidates["ALT-D"]
        ["decision_score"]
        == 0.36
    )

    assert (
        candidates["ALT-D"]
        ["target_delay_min"]
        == 4.49
    )

    assert (
        candidates["ALT-D"]
        ["network_delay_delta_min"]
        == 12.49
    )

    assert (
        candidates["ALT-D"]
        ["affected_flights"]
        == 3
    )

    assert (
        candidates["ALT-D"]
        ["stress_survival"]
        == {
            "passed": 4,
            "total": 5,
        }
    )


def test_approval_executes_through_real_engine_and_verifies(
    client,
):
    run_id = "API-TEST-003"

    recommendation = client.post(
        "/copilot/investigate",
        json=request_payload(run_id),
    )

    assert (
        recommendation.status_code
        == 200
    )

    response = client.post(
        "/copilot/approve",
        json={
            "run_id": run_id,
            "decided_by": (
                "demo_dispatcher"
            ),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["stage"] == (
        "COMPLETE"
    )

    assert body["status"] == (
        "COMPLETED"
    )

    assert (
        body["approval"]["decision"]
        == "APPROVED"
    )

    verification = (
        body["verification_result"]
    )

    assert verification["status"] == (
        "VERIFIED"
    )

    assert verification["source"] == (
        "deterministic engine"
    )

    assert (
        verification["after_metrics"]
        ["verified_at_min"]
        == 21
    )


def test_rejection_creates_new_human_approval_cycle(
    client,
):
    run_id = "API-TEST-004"

    recommendation = client.post(
        "/copilot/investigate",
        json=request_payload(run_id),
    )

    assert (
        recommendation.status_code
        == 200
    )

    assert (
        recommendation.json()
        ["recommendation"]
        ["candidate_id"]
        == "ALT-D"
    )

    response = client.post(
        "/copilot/reject",
        json={
            "run_id": run_id,
            "reason": (
                "Operator prefers another "
                "network trade-off."
            ),
            "decided_by": (
                "demo_dispatcher"
            ),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["stage"] == (
        "DEGRADED"
    )

    assert body["status"] == (
        "DEGRADED"
    )

    assert (
        body["approval"]["decision"]
        == "REJECTED"
    )

    assert (
        body["recommendation"]
        is None
    )

    assert body["leading_candidate_id"] is None

    no_robust = [
        event
        for event in body["events"]
        if event["event_type"] == "NO_ROBUST_INTERVENTION"
    ]
    assert no_robust
    assert (
        no_robust[-1]["data"]["status"]
        == "NO_ROBUST_INTERVENTION_AVAILABLE"
    )


def test_approval_survives_recreated_in_memory_human_gate(
    client,
):
    run_id = "API-TEST-RECOVER-001"

    recommendation = client.post(
        "/copilot/recommend",
        json=request_payload(run_id),
    )

    assert recommendation.status_code == 200
    assert recommendation.json()["approval"]["decision"] == "PENDING"

    with copilot_routes._RUNS_LOCK:
        orchestrator = copilot_routes._RUNS[run_id]

    # Simulate the transient controller-state loss that can occur while the
    # API process remains alive. AgentState remains the authoritative pending
    # decision record and should allow the human gate to be recovered safely.
    orchestrator.approval_controller.clear()

    response = client.post(
        "/copilot/approve",
        json={
            "run_id": run_id,
            "decided_by": "demo_dispatcher",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approval"]["decision"] == "APPROVED"
    assert body["verification_result"]["status"] == "VERIFIED"


def test_unknown_run_cannot_be_approved(
    client,
):
    response = client.post(
        "/copilot/approve",
        json={
            "run_id": (
                "DOES-NOT-EXIST"
            ),
            "decided_by": (
                "demo_dispatcher"
            ),
        },
    )

    assert response.status_code == 404


def test_unknown_run_cannot_be_rejected(
    client,
):
    response = client.post(
        "/copilot/reject",
        json={
            "run_id": (
                "DOES-NOT-EXIST"
            ),
            "reason": (
                "No active recommendation."
            ),
            "decided_by": (
                "demo_dispatcher"
            ),
        },
    )

    assert response.status_code == 404


def test_invalid_decision_time_is_rejected(
    client,
):
    response = client.post(
        "/copilot/investigate",
        json={
            **request_payload(
                "API-TEST-005"
            ),
            "decision_time_min": 241,
        },
    )

    assert response.status_code == 422


def test_reset_clears_active_runs(
    client,
):
    run_id = "API-TEST-006"

    response = client.post(
        "/copilot/investigate",
        json=request_payload(run_id),
    )

    assert (
        response.status_code
        == 200
    )

    response = client.post(
        "/copilot/reset"
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert body["status"] == (
        "RESET"
    )

    assert body["time_min"] == 0

    assert body["scenario_id"] == (
        "mumbai_weather_crisis_v2"
    )

    response = client.post(
        "/copilot/approve",
        json={
            "run_id": run_id,
            "decided_by": (
                "demo_dispatcher"
            ),
        },
    )

    assert response.status_code == 404

def test_duplicate_approval_is_idempotent(client):
    run_id = "API-TEST-DUP-APPROVE"

    recommendation = client.post(
        "/copilot/investigate",
        json=request_payload(run_id),
    )
    assert recommendation.status_code == 200

    payload = {
        "run_id": run_id,
        "decided_by": "demo_dispatcher",
    }

    first = client.post("/copilot/approve", json=payload)
    second = client.post("/copilot/approve", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["approval"]["decision"] == "APPROVED"
    assert second.json()["status"] == "COMPLETED"


def test_duplicate_degraded_rejection_is_idempotent(client):
    run_id = "API-TEST-DUP-REJECT"

    recommendation = client.post(
        "/copilot/investigate",
        json=request_payload(run_id),
    )
    assert recommendation.status_code == 200

    payload = {
        "run_id": run_id,
        "reason": "Dispatcher rejects this recommendation.",
        "decided_by": "demo_dispatcher",
    }

    first = client.post("/copilot/reject", json=payload)
    second = client.post("/copilot/reject", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["approval"]["decision"] == "REJECTED"
    assert second.json()["status"] == "DEGRADED"
