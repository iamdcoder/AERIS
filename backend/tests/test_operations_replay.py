import time

from app.engine import public as engine
from app.operations.replay import ReplayController


def test_replay_reset_and_manual_step_does_not_mutate_authoritative_engine():
    engine.reset_engine()
    assert engine.get_airspace_state()["time_min"] == 0

    controller = ReplayController(tick_seconds=0.05)
    snapshot = controller.reset(stop_at_minute=3)
    assert snapshot.last_simulation_time_min == 0
    assert snapshot.running is False
    assert snapshot.done is False
    assert snapshot.recent_events
    assert engine.get_airspace_state()["time_min"] == 0

    snapshot = controller.step(1)
    assert snapshot.last_simulation_time_min == 1
    assert snapshot.last_sequence >= 1
    assert snapshot.entities["airspace"]["CURRENT"]["time_min"] == 1
    assert engine.get_airspace_state()["time_min"] == 0


def test_replay_reaches_stop_minute_without_advancing_authoritative_engine():
    engine.reset_engine()
    controller = ReplayController(tick_seconds=0.02)
    controller.reset(stop_at_minute=2)
    controller.start(reset_first=False)

    deadline = time.time() + 1
    while controller.snapshot().running and time.time() < deadline:
        time.sleep(0.02)

    snapshot = controller.snapshot()
    assert snapshot.done is True
    assert snapshot.running is False
    assert snapshot.last_simulation_time_min == 2
    assert snapshot.entities["airspace"]["CURRENT"]["time_min"] == 2
    assert engine.get_airspace_state()["time_min"] == 0


def test_replay_sync_to_authoritative_engine_preserves_engine_state():
    engine.reset_engine()
    engine.advance_simulation(5)

    controller = ReplayController(tick_seconds=0.05)
    snapshot = controller.sync_current_engine()

    assert snapshot.last_simulation_time_min == 5
    assert snapshot.entities["airspace"]["CURRENT"]["time_min"] == 5
    assert engine.get_airspace_state()["time_min"] == 5
