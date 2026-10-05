from datetime import datetime, timezone

import pytest

from app.operations.events import OperationalEventType, make_event
from app.operations.state import OperationalStateStore


def event(sequence: int, *, event_type=OperationalEventType.SYSTEM_ALERT, entity_id="S1"):
    return make_event(
        event_id=f"E{sequence}",
        sequence=sequence,
        event_type=event_type,
        source="TEST",
        occurred_at=datetime.now(timezone.utc),
        simulation_time_min=sequence,
        entity_type="sector",
        entity_id=entity_id,
        payload={"value": sequence},
    )


def test_apply_event_updates_state():
    store = OperationalStateStore()
    snapshot = store.apply_event(event(0))
    assert snapshot.version == 1
    assert snapshot.last_sequence == 0
    assert snapshot.last_simulation_time_min == 0
    assert snapshot.entities["sector"]["S1"]["value"] == 0
    assert len(snapshot.recent_events) == 1


def test_apply_event_rejects_duplicate_or_out_of_order_sequence():
    store = OperationalStateStore()
    store.apply_event(event(5))
    with pytest.raises(ValueError):
        store.apply_event(event(5))
    with pytest.raises(ValueError):
        store.apply_event(event(4))


def test_disruption_lifecycle():
    store = OperationalStateStore()
    store.apply_event(
        event(
            0,
            event_type=OperationalEventType.DISRUPTION_DETECTED,
            entity_id="WX-1",
        )
    )
    assert "WX-1" in store.snapshot().active_disruptions

    store.apply_event(
        event(
            1,
            event_type=OperationalEventType.DISRUPTION_CLEARED,
            entity_id="WX-1",
        )
    )
    assert "WX-1" not in store.snapshot().active_disruptions


def test_recent_events_and_events_since():
    store = OperationalStateStore(max_recent_events=3)
    for sequence in range(5):
        store.apply_event(event(sequence))

    recent = store.recent_events(2)
    assert [item.sequence for item in recent] == [4, 3]
    assert [item.sequence for item in store.events_since(2)] == [3, 4]


def test_latest_entity_and_reset():
    store = OperationalStateStore()
    store.apply_event(event(0))
    assert store.latest_entity("sector", "S1") == {"value": 0}
    assert store.latest_entity("sector", "UNKNOWN") is None

    store.reset()
    snapshot = store.snapshot()
    assert snapshot.version == 0
    assert snapshot.last_sequence == -1
    assert snapshot.entities == {}
    assert snapshot.recent_events == []
