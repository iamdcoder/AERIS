from datetime import datetime, timezone

import pytest

from app.operations.events import (
    OperationalEventType,
    OperationalStateSnapshot,
    make_event,
    OperationalEvent,
)


def test_operational_event_normalizes_severity():
    event = make_event(
        event_id="E1",
        sequence=0,
        event_type=OperationalEventType.WEATHER_UPDATE,
        source="TEST",
        occurred_at=datetime.now(timezone.utc),
        entity_type="weather_cell",
        entity_id="WX-1",
        severity="high",
        payload={"intensity": "HIGH"},
    )
    assert event.severity == "HIGH"
    assert event.model_dump(mode="json")["event_type"] == "WEATHER_UPDATE"


def test_operational_event_rejects_invalid_values():
    with pytest.raises(ValueError):
        OperationalEvent(
            event_id="",
            sequence=0,
            event_type=OperationalEventType.SYSTEM_ALERT,
            source="TEST",
            occurred_at=datetime.now(timezone.utc),
            entity_type="scenario",
            entity_id="S",
            severity="INFO",
        )

    with pytest.raises(ValueError):
        OperationalEvent(
            event_id="E2",
            sequence=-1,
            event_type=OperationalEventType.SYSTEM_ALERT,
            source="TEST",
            occurred_at=datetime.now(timezone.utc),
            entity_type="scenario",
            entity_id="S",
            severity="INFO",
        )

    with pytest.raises(ValueError):
        OperationalEvent(
            event_id="E3",
            sequence=1,
            event_type=OperationalEventType.SYSTEM_ALERT,
            source="TEST",
            occurred_at=datetime.now(timezone.utc),
            entity_type="scenario",
            entity_id="S",
            severity="UNKNOWN",
        )


def test_state_snapshot_is_json_serializable():
    snapshot = OperationalStateSnapshot(version=0, last_sequence=-1)
    encoded = snapshot.model_dump(mode="json")
    assert encoded["version"] == 0
    assert encoded["last_sequence"] == -1
