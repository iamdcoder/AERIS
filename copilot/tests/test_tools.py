from copilot.mock_engine import MockEngineClient


def test_mock_engine_loads_deterministic_state():
    engine = MockEngineClient()

    first = engine.get_state()
    second = engine.get_state()

    assert first == second

    assert (
        first["mode"]
        == "DETERMINISTIC_MOCK"
    )

    assert (
        first["target_flight_id"]
        == "F102"
    )

    assert (
        engine.healthcheck()["deterministic"]
        is True
    )


def test_mock_engine_returns_five_candidates():
    engine = MockEngineClient()

    candidates = (
        engine.get_alternatives("F102")
    )

    assert len(candidates) == 5

    assert {
        item["candidate_id"]
        for item in candidates
    } == {
        "ALT-A",
        "ALT-B",
        "ALT-C",
        "ALT-D",
        "ALT-E",
    }


def test_mock_engine_does_not_expose_mutable_internal_state():
    engine = MockEngineClient()

    state = engine.get_state()

    state[
        "network_summary"
    ][
        "active_aircraft"
    ] = 999

    fresh = engine.get_state()

    assert (
        fresh[
            "network_summary"
        ][
            "active_aircraft"
        ]
        == 48
    )