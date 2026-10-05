"""Thread-safe normalized operational state store."""
from __future__ import annotations

from copy import deepcopy
from threading import RLock

from .events import OperationalEvent, OperationalEventType, OperationalStateSnapshot


class OperationalStateStore:
    """Maintain the latest normalized operational state and a bounded event journal."""

    def __init__(self, *, max_recent_events: int = 100) -> None:
        if max_recent_events < 1:
            raise ValueError("max_recent_events must be at least 1")
        self._lock = RLock()
        self._max_recent_events = max_recent_events
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._version = 0
            self._last_sequence = -1
            self._last_simulation_time_min = None
            self._entities: dict[str, dict[str, dict]] = {}
            self._active_disruptions: dict[str, dict] = {}
            self._recent_events: list[OperationalEvent] = []

    def apply_event(
        self,
        event: OperationalEvent,
    ) -> OperationalStateSnapshot:
        with self._lock:
            if event.sequence <= self._last_sequence:
                raise ValueError(
                    f"Event sequence must increase strictly: "
                    f"{event.sequence} <= {self._last_sequence}"
                )

            self._last_sequence = event.sequence
            if event.simulation_time_min is not None:
                self._last_simulation_time_min = event.simulation_time_min

            entity_bucket = self._entities.setdefault(event.entity_type, {})
            entity_bucket[event.entity_id] = deepcopy(event.payload)

            self._recent_events.append(deepcopy(event))
            self._recent_events = self._recent_events[-self._max_recent_events :]

            if event.event_type == OperationalEventType.DISRUPTION_DETECTED:
                self._active_disruptions[event.entity_id] = deepcopy(event.payload)
            elif event.event_type == OperationalEventType.DISRUPTION_CLEARED:
                self._active_disruptions.pop(event.entity_id, None)

            self._version += 1
            return self.snapshot()

    def snapshot(self) -> OperationalStateSnapshot:
        with self._lock:
            return OperationalStateSnapshot(
                version=self._version,
                last_sequence=self._last_sequence,
                last_simulation_time_min=self._last_simulation_time_min,
                entities=deepcopy(self._entities),
                active_disruptions=deepcopy(self._active_disruptions),
                recent_events=deepcopy(self._recent_events),
            )

    def recent_events(self, limit: int = 20) -> list[OperationalEvent]:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if limit == 0:
            return []
        with self._lock:
            return deepcopy(list(reversed(self._recent_events[-limit:])))

    def latest_entity(self, entity_type: str, entity_id: str) -> dict | None:
        with self._lock:
            payload = self._entities.get(entity_type, {}).get(entity_id)
            return deepcopy(payload) if payload is not None else None

    def events_since(self, sequence: int) -> list[OperationalEvent]:
        with self._lock:
            return deepcopy(
                [event for event in self._recent_events if event.sequence > sequence]
            )
