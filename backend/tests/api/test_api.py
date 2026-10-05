"""Integration tests for the AERIS FastAPI layer.

These tests exercise every contract endpoint defined in contracts/api-contract.md.
They use FastAPI's TestClient so no real server is needed.

The API must ONLY orchestrate engine calls — it must NOT duplicate engine logic.
Each test verifies the transport contract, status codes, and response shapes.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.engine import public as engine


@pytest.fixture(autouse=True)
def reset_engine():
    """Ensure a fresh engine between every test."""
    engine.reset_engine()
    yield
    engine.reset_engine()


@pytest.fixture(scope="module")
def client():
    """Module-scoped TestClient; engine is reset per-test via autouse fixture."""
    return TestClient(create_app(), raise_server_exceptions=True)


# ── TEST 1: GET /health ──────────────────────────────────────────────────────

def test_health_returns_200_and_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "aeris"


# ── TEST 2: GET /airspace ────────────────────────────────────────────────────

def test_airspace_returns_snapshot_with_expected_keys(client):
    resp = client.get("/airspace")
    assert resp.status_code == 200
    body = resp.json()
    assert "aircraft" in body
    assert "weather_cells" in body
    assert "sectors" in body
    assert "airports" in body
    assert "time_min" in body
    assert body["time_min"] == 0


def test_airspace_contains_flagship_flight(client):
    body = client.get("/airspace").json()
    aircraft_ids = {f["id"] for f in body["aircraft"]}
    assert "F102" in aircraft_ids


def test_airspace_aircraft_have_required_fields(client):
    body = client.get("/airspace").json()
    for flight in body["aircraft"]:
        fid = flight.get("id", "?")
        assert "status" in flight, f"Flight {fid} missing 'status'"
        assert "route" in flight, f"Flight {fid} missing 'route'"


# ── TEST 3: GET /flights/{flight_id} ─────────────────────────────────────────

def test_get_flight_returns_f102(client):
    resp = client.get("/flights/F102")
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert "status" in body
    assert "route" in body
    assert body.get("id") == "F102"


def test_get_flight_returns_404_for_unknown(client):
    resp = client.get("/flights/NONEXISTENT")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── TEST 4: GET /disruptions ─────────────────────────────────────────────────

def test_disruptions_returns_correct_keys(client):
    resp = client.get("/disruptions")
    assert resp.status_code == 200
    body = resp.json()
    assert "weather_cells" in body
    assert "restrictions" in body
    assert "time_min" in body


def test_disruptions_at_t0_has_one_weather_cell(client):
    body = client.get("/disruptions").json()
    # Mumbai scenario has WX-BOM-01 from t=0; weather_cells may be a list or dict
    wc = body["weather_cells"]
    count = len(wc) if isinstance(wc, (list, dict)) else 0
    assert count >= 1


# ── TEST 5: GET /network/metrics ─────────────────────────────────────────────

def test_network_metrics_returns_contract_fields(client):
    resp = client.get("/network/metrics")
    assert resp.status_code == 200
    body = resp.json()
    required = {
        "time_min",
        "total_delay_min",
        "airborne_flights",
        "holding_flights",
        "total_flights",
        "sector_utilization",
        "airports",
    }
    assert required.issubset(body.keys())


def test_network_metrics_counts_are_non_negative(client):
    body = client.get("/network/metrics").json()
    assert body["airborne_flights"] >= 0
    assert body["holding_flights"] >= 0
    assert body["total_flights"] >= 0
    assert body["total_delay_min"] >= 0


# ── TEST 6: POST /alternatives ───────────────────────────────────────────────

def test_alternatives_returns_five_candidates_for_f102(client):
    resp = client.post("/alternatives", json={"flight_id": "F102"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["flight_id"] == "F102"
    assert len(body["candidates"]) == 5


def test_alternatives_candidate_ids_are_expected(client):
    body = client.post("/alternatives", json={"flight_id": "F102"}).json()
    ids = {c["candidate_id"] for c in body["candidates"]}
    assert ids == {"ALT-A", "ALT-B", "ALT-C", "ALT-D", "ALT-E"}


def test_alternatives_returns_422_for_unknown_flight(client):
    resp = client.post("/alternatives", json={"flight_id": "GHOST"})
    assert resp.status_code == 422


# ── TEST 7: POST /validate ───────────────────────────────────────────────────

def _get_candidate(client, candidate_id: str = "ALT-A") -> dict:
    candidates = client.post("/alternatives", json={"flight_id": "F102"}).json()["candidates"]
    return next(c for c in candidates if c["candidate_id"] == candidate_id)


def test_validate_returns_feasibility_and_constraint_results(client):
    candidate = _get_candidate(client, "ALT-A")
    resp = client.post("/validate", json=candidate)
    assert resp.status_code == 200
    body = resp.json()
    assert "feasible" in body
    assert "constraint_results" in body
    assert "rejection_reasons" in body
    assert "weather_risk" in body


def test_validate_constraint_results_has_all_sub_keys(client):
    candidate = _get_candidate(client, "ALT-A")
    body = client.post("/validate", json=candidate).json()
    sub = body["constraint_results"]
    required = {"route", "weather", "fuel", "capacity", "conflict", "restriction"}
    assert required.issubset(sub.keys())


def test_validate_returns_422_for_malformed_candidate(client):
    resp = client.post("/validate", json={"candidate_id": "X"})
    assert resp.status_code == 422


# ── TEST 8: POST /simulate ───────────────────────────────────────────────────

def test_simulate_returns_network_impact_fields(client):
    candidate = _get_candidate(client, "ALT-A")
    resp = client.post("/simulate", json=candidate)
    assert resp.status_code == 200
    body = resp.json()
    # Must contain at minimum the candidate_id echo and delay info
    assert "candidate_id" in body
    assert "target_delay_delta_min" in body


def test_simulate_result_is_json_serializable(client):
    import json
    candidate = _get_candidate(client, "ALT-B")
    body = client.post("/simulate", json=candidate).json()
    # Already JSON since it came from TestClient, but verify no NaN/Inf leakage
    json.dumps(body)


# ── TEST 9: POST /stress-test ────────────────────────────────────────────────

def test_stress_test_returns_survivability_report(client):
    candidate = _get_candidate(client, "ALT-A")
    resp = client.post("/stress-test", json=candidate)
    assert resp.status_code == 200
    body = resp.json()
    assert "passed" in body
    assert "total" in body
    assert body["total"] == 5  # five scenario stress test


def test_stress_test_report_has_results_and_failure_details(client):
    candidate = _get_candidate(client, "ALT-A")
    body = client.post("/stress-test", json=candidate).json()
    # Report must have deterministic structure regardless of survival count
    assert "passed" in body
    assert "total" in body
    assert "survival_pct" in body
    assert "results" in body
    assert len(body["results"]) == body["total"]
    for result in body["results"]:
        assert "scenario_id" in result
        assert "passed" in result
        assert "max_sector_utilization_pct" in result


# ── TEST 10: POST /decision-score ────────────────────────────────────────────

def test_decision_score_returns_ranked_list(client):
    candidates = client.post("/alternatives", json={"flight_id": "F102"}).json()["candidates"]
    resp = client.post("/decision-score", json={"candidates": candidates})
    assert resp.status_code == 200
    body = resp.json()
    assert "scored_candidates" in body
    scored = body["scored_candidates"]
    assert len(scored) == 5

    scores = [c["decision_score"] for c in scored]
    assert scores == sorted(scores, reverse=True), "Results must be ranked highest→lowest"


def test_decision_score_each_has_contract_fields(client):
    candidates = client.post("/alternatives", json={"flight_id": "F102"}).json()["candidates"]
    scored = client.post("/decision-score", json={"candidates": candidates}).json()["scored_candidates"]
    for c in scored:
        assert "candidate_id" in c
        assert "feasible" in c
        assert "decision_score" in c


# ── TEST 11: POST /apply ─────────────────────────────────────────────────────

def test_apply_without_approval_flag_returns_403(client):
    candidates = client.post("/alternatives", json={"flight_id": "F102"}).json()["candidates"]
    candidate_id = candidates[0]["candidate_id"]
    resp = client.post("/apply", json={"candidate_id": candidate_id, "approved": False})
    assert resp.status_code == 403


def test_apply_with_approval_returns_executing_status(client):
    candidates = client.post("/alternatives", json={"flight_id": "F102"}).json()["candidates"]
    # ALT-A should be feasible at t=0
    candidate_id = "ALT-A"
    resp = client.post("/apply", json={"candidate_id": candidate_id, "approved": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "EXECUTING"
    assert body["candidate_id"] == candidate_id
    assert body["flight_id"] == "F102"


def test_apply_unknown_candidate_returns_422(client):
    resp = client.post("/apply", json={"candidate_id": "MISSING", "approved": True})
    assert resp.status_code == 422


# ── TEST 12: POST /verify ────────────────────────────────────────────────────

def test_verify_without_prior_apply_returns_422(client):
    resp = client.post("/verify", json={"candidate_id": "ALT-A"})
    assert resp.status_code == 422


def test_verify_after_apply_returns_status_and_contract_fields(client):
    # Generate + apply ALT-A
    client.post("/alternatives", json={"flight_id": "F102"})
    client.post("/apply", json={"candidate_id": "ALT-A", "approved": True})

    resp = client.post("/verify", json={"candidate_id": "ALT-A"})
    assert resp.status_code == 200
    body = resp.json()
    required = {
        "status",
        "target_delay_delta_min",
        "affected_flights",
        "network_delay_delta_min",
        "constraints_safe",
        "new_degradation",
        "reassessment_required",
    }
    assert required.issubset(body.keys())
    assert body["status"] in ("VERIFIED", "REASSESSMENT_REQUIRED")


def test_verify_wrong_candidate_returns_422(client):
    client.post("/alternatives", json={"flight_id": "F102"})
    client.post("/apply", json={"candidate_id": "ALT-A", "approved": True})
    resp = client.post("/verify", json={"candidate_id": "ALT-B"})
    assert resp.status_code == 422


# ── TEST 13: Response shape consistency ──────────────────────────────────────

def test_all_read_endpoints_return_200_at_t0(client):
    for path in ["/health", "/airspace", "/disruptions", "/network/metrics"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"GET {path} returned {resp.status_code}"


def test_openapi_schema_is_generated(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    # Verify all contract endpoints are registered
    paths = set(schema["paths"].keys())
    contract_paths = {
        "/health", "/airspace", "/disruptions", "/network/metrics",
        "/alternatives", "/validate", "/simulate", "/stress-test",
        "/decision-score", "/apply", "/verify",
        "/copilot/investigate", "/copilot/recommend",
    }
    for path in contract_paths:
        assert path in paths, f"Contract path {path!r} missing from OpenAPI schema"
