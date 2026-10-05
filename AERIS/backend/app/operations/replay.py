"""Deterministic operational event replay used as AERIS' simulated live source.

The replay owns an independent digital-twin simulator. Creating, resetting, or
advancing this controller MUST NOT mutate the authoritative decision engine.
This separation lets the live feed run concurrently with an in-progress AERIS
decision without corrupting its snapshot.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import threading
from typing import Any

from ..engine.digital_twin.loaders import load_world
from ..engine.digital_twin.simulator import DigitalTwinSimulator
from ..engine import public as authoritative_engine
from .events import (
    OperationalEvent,
    OperationalEventType,
    OperationalStateSnapshot,
    make_event,
)
from .state import OperationalStateStore


FLAGSHIP_SCENARIO_ID = "mumbai_weather_crisis_v2"
FLAGSHIP_TARGET_FLIGHT = "F102"


_EVENT_MAP: dict[str, tuple[OperationalEventType, str, str]] = {
    "convective_weather_develops_near_BOM": (
        OperationalEventType.WEATHER_UPDATE,
        "weather_cell",
        "WX-BOM-01",
    ),
    "BOM_arrival_capacity_drops": (
        OperationalEventType.AIRPORT_CAPACITY_UPDATE,
        "airport",
        "BOM",
    ),
    "holding_begins": (
        OperationalEventType.TRAFFIC_UPDATE,
        "network",
        "BOM",
    ),
    "bypass_sector_approaches_capacity": (
        OperationalEventType.SECTOR_CAPACITY_UPDATE,
        "sector",
        "S6",
    ),
    "F102_operational_degradation": (
        OperationalEventType.FLIGHT_STATE_UPDATE,
        "aircraft",
        FLAGSHIP_TARGET_FLIGHT,
    ),
    "activate_temporary_restriction": (
        OperationalEventType.RESTRICTION_UPDATE,
        "restriction",
        "R-MONSOON-01",
    ),
}


class ReplayController:
    """Thread-safe minute-by-minute replay isolated from the decision engine."""

    def __init__(self, *, tick_seconds: float = 0.8) -> None:
        if tick_seconds <= 0:
            raise ValueError("tick_seconds must be positive")

        self._lock = threading.RLock()
        self._store = OperationalStateStore(max_recent_events=120)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._running = False
        self._tick_seconds = float(tick_seconds)
        self._stop_at_minute = 19
        self._scenario_id = FLAGSHIP_SCENARIO_ID
        self._next_sequence = 0
        self._last_updated_at: datetime | None = None
        self._simulation_epoch: datetime = datetime.now(timezone.utc)
        self._simulator = DigitalTwinSimulator(load_world())

        # Construction is intentionally non-destructive.  Populate only the
        # replay's own baseline state; do not touch the authoritative engine.
        self._initialize_baseline()

    def _initialize_baseline(self) -> None:
        with self._lock:
            self._store.reset()
            self._next_sequence = 0
            self._simulator = DigitalTwinSimulator(load_world())
            self._simulation_epoch = datetime.now(timezone.utc)
            self._last_updated_at = self._simulation_epoch
            self._running = False
            self._stop_event.set()
            self._emit(
                event_type=OperationalEventType.SYSTEM_ALERT,
                entity_type="scenario",
                entity_id=self._scenario_id,
                simulation_time_min=0,
                severity="INFO",
                payload={
                    "title": "Baseline operational state",
                    "message": "AERIS replay initialized at T+00.",
                    "target_flight_id": FLAGSHIP_TARGET_FLIGHT,
                },
                occurred_at=self._event_time(0),
            )
            self._sync_current_replay_state()

    def _event_time(self, simulation_time_min: int) -> datetime:
        return self._simulation_epoch + timedelta(minutes=max(0, simulation_time_min))

    def reset(self, *, stop_at_minute: int = 19) -> OperationalStateSnapshot:
        """Reset only the simulated live feed to T+00."""
        if stop_at_minute < 0:
            raise ValueError("stop_at_minute must be non-negative")

        self.stop()
        with self._lock:
            self._stop_at_minute = int(stop_at_minute)
            self._scenario_id = FLAGSHIP_SCENARIO_ID
            self._initialize_baseline()
            return self._snapshot_locked()

    def sync_current_engine(self) -> OperationalStateSnapshot:
        """Synchronize the replay to the authoritative engine time without mutating it.

        The flagship decision engine is reset/advanced by the Copilot API.  This
        method rebuilds the independent replay to that same simulated minute so
        the UI can show the corresponding operational state.
        """
        self.stop()
        with self._lock:
            authoritative_snapshot = authoritative_engine.get_airspace_state()
            target_time = int(authoritative_snapshot.get("time_min", 0))
            self._stop_at_minute = max(self._stop_at_minute, target_time)
            self._store.reset()
            self._next_sequence = 0
            self._simulator = DigitalTwinSimulator(load_world())
            self._simulation_epoch = datetime.now(timezone.utc) - timedelta(minutes=target_time)
            self._last_updated_at = self._simulation_epoch
            self._running = False
            self._stop_event.set()

            self._emit(
                event_type=OperationalEventType.SYSTEM_ALERT,
                entity_type="scenario",
                entity_id=self._scenario_id,
                simulation_time_min=0,
                severity="INFO",
                payload={
                    "title": "Operational state synchronized",
                    "message": "AERIS live feed synchronized to the decision engine timeline.",
                    "target_flight_id": FLAGSHIP_TARGET_FLIGHT,
                },
                occurred_at=self._event_time(0),
            )

            for _ in range(target_time):
                self._advance_one_minute()

            return self._snapshot_locked()

    def set_tick_seconds(self, seconds: float) -> None:
        if seconds <= 0:
            raise ValueError("seconds must be positive")
        with self._lock:
            self._tick_seconds = float(seconds)

    def start(
        self,
        *,
        stop_at_minute: int | None = None,
        reset_first: bool = False,
    ) -> OperationalStateSnapshot:
        if reset_first:
            self.reset(stop_at_minute=stop_at_minute or self._stop_at_minute)

        with self._lock:
            if stop_at_minute is not None:
                if stop_at_minute < 0:
                    raise ValueError("stop_at_minute must be non-negative")
                self._stop_at_minute = int(stop_at_minute)

            current = int(self._simulator.state.time_min)
            if current >= self._stop_at_minute:
                self._running = False
                self._stop_event.set()
                return self._snapshot_locked()

            if self._running:
                return self._snapshot_locked()

            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="aeris-operational-replay",
                daemon=True,
            )
            self._thread.start()
            return self._snapshot_locked()

    def stop(self) -> OperationalStateSnapshot:
        with self._lock:
            self._running = False
            self._stop_event.set()
            thread = self._thread
            self._thread = None

        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=max(1.0, self._tick_seconds + 0.5))

        with self._lock:
            return self._snapshot_locked()

    def step(self, minutes: int = 1) -> OperationalStateSnapshot:
        if minutes < 1:
            raise ValueError("minutes must be at least 1")
        self.stop()
        for _ in range(minutes):
            with self._lock:
                if self._simulator.state.time_min >= self._stop_at_minute:
                    break
            self._advance_one_minute()
        with self._lock:
            return self._snapshot_locked()

    def snapshot(self) -> OperationalStateSnapshot:
        with self._lock:
            return self._snapshot_locked()

    def events(self, limit: int = 20) -> list[OperationalEvent]:
        return self._store.recent_events(limit)

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self._tick_seconds):
            with self._lock:
                if not self._running or self._simulator.state.time_min >= self._stop_at_minute:
                    self._running = False
                    break
            try:
                self._advance_one_minute()
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                with self._lock:
                    self._running = False
                    self._stop_event.set()
                    self._emit_system_alert(
                        title="Replay error",
                        message=str(exc),
                        severity="CRITICAL",
                    )
                break

        with self._lock:
            self._running = False

    def _advance_one_minute(self) -> None:
        with self._lock:
            if self._simulator.state.time_min >= self._stop_at_minute:
                self._running = False
                self._stop_event.set()
                return

            previous_event_count = len(self._simulator.state.event_log)
            state = self._simulator.advance(1)
            sim_time = int(state.time_min)
            new_logs = state.event_log[previous_event_count:]

            for item in new_logs:
                self._emit_engine_event(item, sim_time)

            self._emit_snapshot_events(state)

            if sim_time >= self._stop_at_minute:
                self._running = False
                self._stop_event.set()

    def _emit_snapshot_events(self, state: Any) -> None:
        target = state.aircraft.get(FLAGSHIP_TARGET_FLIGHT)
        sim_time = int(state.time_min)
        if target is not None:
            self._emit(
                event_type=OperationalEventType.SURVEILLANCE_UPDATE,
                entity_type="aircraft",
                entity_id=FLAGSHIP_TARGET_FLIGHT,
                simulation_time_min=sim_time,
                severity="HIGH" if target.status == "DEGRADED" else "INFO",
                payload={
                    "status": target.status,
                    "position": target.position.model_dump(),
                    "altitude_ft": target.altitude_ft,
                    "speed_kt": target.speed_kt,
                    "fuel_remaining_min": target.fuel_remaining_min,
                    "delay_min": target.delay_min,
                },
                occurred_at=self._event_time(sim_time),
            )

    def _emit_engine_event(self, item: dict[str, Any], simulation_time_min: int) -> None:
        event_name = str(item.get("event", "system_event"))
        payload = deepcopy(item.get("payload", {}))
        mapped = _EVENT_MAP.get(event_name)

        if mapped:
            event_type, entity_type, default_entity_id = mapped
            entity_id = str(
                payload.get("flight_id")
                or payload.get("airport_id")
                or payload.get("sector_id")
                or payload.get("restriction_id")
                or default_entity_id
            )
            severity = (
                "HIGH"
                if event_name in {
                    "convective_weather_develops_near_BOM",
                    "F102_operational_degradation",
                }
                else "MEDIUM"
            )
            self._emit(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                simulation_time_min=simulation_time_min,
                severity=severity,
                payload={"source_event": event_name, **payload},
                occurred_at=self._event_time(simulation_time_min),
            )
            return

        self._emit(
            event_type=OperationalEventType.SYSTEM_ALERT,
            entity_type="scenario",
            entity_id=self._scenario_id,
            simulation_time_min=simulation_time_min,
            severity="INFO",
            payload={"source_event": event_name, **payload},
            occurred_at=self._event_time(simulation_time_min),
        )

    def _emit_system_alert(self, *, title: str, message: str, severity: str) -> None:
        sim_time = int(self._simulator.state.time_min)
        self._emit(
            event_type=OperationalEventType.SYSTEM_ALERT,
            entity_type="scenario",
            entity_id=self._scenario_id,
            simulation_time_min=sim_time,
            severity=severity,
            payload={"title": title, "message": message},
            occurred_at=datetime.now(timezone.utc),
        )

    def _emit(
        self,
        *,
        event_type: OperationalEventType,
        entity_type: str,
        entity_id: str,
        simulation_time_min: int,
        severity: str,
        payload: dict[str, Any],
        occurred_at: datetime,
    ) -> OperationalEvent:
        event = make_event(
            event_id=f"REPLAY-{self._next_sequence:04d}",
            sequence=self._next_sequence,
            event_type=event_type,
            source="AERIS_SCENARIO_REPLAY",
            occurred_at=occurred_at,
            simulation_time_min=simulation_time_min,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
            payload=payload,
            scenario_id=self._scenario_id,
        )
        self._next_sequence += 1
        self._store.apply_event(event)
        self._last_updated_at = occurred_at
        return event

    def _sync_current_replay_state(self) -> None:
        airspace = self._simulator.state.snapshot()
        self._store.apply_event(
            make_event(
                event_id=f"REPLAY-{self._next_sequence:04d}",
                sequence=self._next_sequence,
                event_type=OperationalEventType.SYSTEM_ALERT,
                source="AERIS_SCENARIO_REPLAY",
                occurred_at=self._event_time(int(airspace["time_min"])),
                simulation_time_min=int(airspace["time_min"]),
                entity_type="airspace",
                entity_id="CURRENT",
                severity="INFO",
                payload=airspace,
                scenario_id=self._scenario_id,
            )
        )
        self._next_sequence += 1

    def _snapshot_locked(self) -> OperationalStateSnapshot:
        airspace = self._simulator.state.snapshot()
        snapshot = self._store.snapshot()
        snapshot.running = self._running
        snapshot.stop_at_minute = self._stop_at_minute
        snapshot.done = int(airspace.get("time_min", 0)) >= self._stop_at_minute
        snapshot.last_updated_at = self._last_updated_at
        snapshot.scenario_id = self._scenario_id
        snapshot.source = "SIMULATED_OPERATIONAL_FEED"
        snapshot.entities = deepcopy(snapshot.entities)
        snapshot.entities.setdefault("airspace", {})["CURRENT"] = deepcopy(airspace)
        snapshot.last_simulation_time_min = int(airspace.get("time_min", 0))
        snapshot.recent_events = list(reversed(snapshot.recent_events))
        return snapshot


_REPLAY_CONTROLLER: ReplayController | None = None
_REPLAY_LOCK = threading.Lock()


def get_replay_controller() -> ReplayController:
    """Return the process-wide isolated replay controller."""
    global _REPLAY_CONTROLLER
    with _REPLAY_LOCK:
        if _REPLAY_CONTROLLER is None:
            _REPLAY_CONTROLLER = ReplayController()
        return _REPLAY_CONTROLLER
