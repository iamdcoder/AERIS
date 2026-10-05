from fastapi.testclient import TestClient

from app.api.app import create_app


def test_live_operations_api_lifecycle():
    client = TestClient(create_app())

    response = client.post("/operations/replay/reset")
    assert response.status_code == 200
    assert response.json()["last_simulation_time_min"] == 0

    response = client.post(
        "/operations/replay/step",
        json={"minutes": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["last_simulation_time_min"] == 2
    assert body["entities"]["airspace"]["CURRENT"]["time_min"] == 2

    response = client.get("/operations/events?limit=5")
    assert response.status_code == 200
    assert response.json()["events"]


def test_live_operations_api_validates_requests():
    client = TestClient(create_app())
    assert (
        client.post(
            "/operations/replay/step",
            json={"minutes": 0},
        ).status_code
        == 422
    )
    assert (
        client.get("/operations/events?limit=0").status_code
        == 422
    )


def test_live_operations_websocket_streams_snapshot():
    client = TestClient(create_app())
    response = client.post(
        "/operations/replay/reset",
        json={},
    )
    assert response.status_code == 200

    with client.websocket_connect("/ws/operations") as websocket:
        message = websocket.receive_json()
        assert message["source"] == "SIMULATED_OPERATIONAL_FEED"
        assert message["last_simulation_time_min"] == 0
        assert "recent_events" in message
