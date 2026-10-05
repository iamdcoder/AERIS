"""Canonical operational event model for AERIS Phase 3A."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator, model_validator


class OperationalEventType(str, Enum):
    SURVEILLANCE_UPDATE = "SURVEILLANCE_UPDATE"
    WEATHER_UPDATE = "WEATHER_UPDATE"
    SECTOR_CAPACITY_UPDATE = "SECTOR_CAPACITY_UPDATE"
    AIRPORT_CAPACITY_UPDATE = "AIRPORT_CAPACITY_UPDATE"
    TRAFFIC_UPDATE = "TRAFFIC_UPDATE"
    RESTRICTION_UPDATE = "RESTRICTION_UPDATE"
    FLIGHT_STATE_UPDATE = "FLIGHT_STATE_UPDATE"
    DISRUPTION_DETECTED = "DISRUPTION_DETECTED"
    DISRUPTION_CLEARED = "DISRUPTION_CLEARED"
    SYSTEM_ALERT = "SYSTEM_ALERT"


_VALID_SEVERITIES = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


class OperationalEvent(BaseModel):
    event_id: str
    sequence: int
    event_type: OperationalEventType
    source: str
    occurred_at: datetime

    simulation_time_min: int | None = None

    entity_type: str
    entity_id: str

    severity: str = "INFO"

    payload: dict[str, Any] = {}

    scenario_id: str | None = None
    correlation_id: str | None = None

    @field_validator("event_id", "entity_type", "entity_id", "source")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v

    @field_validator("sequence")
    @classmethod
    def _sequence_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("sequence must be >= 0")
        return v

    @field_validator("simulation_time_min")
    @classmethod
    def _sim_time_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("simulation_time_min must be >= 0 when supplied")
        return v

    @field_validator("severity")
    @classmethod
    def _severity_valid(cls, v: str) -> str:
        upper = v.upper()
        if upper not in _VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(_VALID_SEVERITIES)}, got '{v}'")
        return upper

    @field_validator("payload")
    @classmethod
    def _payload_is_dict(cls, v: Any) -> dict:
        if not isinstance(v, dict):
            raise ValueError("payload must be a dictionary")
        return v


def make_event(
    *,
    event_id: str,
    sequence: int,
    event_type: OperationalEventType,
    source: str,
    occurred_at: datetime,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any],
    simulation_time_min: int | None = None,
    severity: str = "INFO",
    scenario_id: str | None = None,
    correlation_id: str | None = None,
) -> OperationalEvent:
    """Convenience constructor — no business logic."""
    return OperationalEvent(
        event_id=event_id,
        sequence=sequence,
        event_type=event_type,
        source=source,
        occurred_at=occurred_at,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        simulation_time_min=simulation_time_min,
        severity=severity,
        scenario_id=scenario_id,
        correlation_id=correlation_id,
    )
