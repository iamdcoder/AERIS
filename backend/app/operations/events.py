"""Canonical operational event contracts used by AERIS live data sources."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OperationalEventType(str, Enum):
    """Normalized categories emitted by operational data sources."""

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


_ALLOWED_SEVERITIES = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


class OperationalEvent(BaseModel):
    """Stable JSON-friendly event passed between ingestion and AERIS."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    event_type: OperationalEventType
    source: str = Field(min_length=1)
    occurred_at: datetime
    simulation_time_min: int | None = Field(default=None, ge=0)
    entity_type: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    severity: str = "INFO"
    payload: dict[str, Any] = Field(default_factory=dict)
    scenario_id: str | None = None
    correlation_id: str | None = None

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in _ALLOWED_SEVERITIES:
            raise ValueError(
                "severity must be one of INFO, LOW, MEDIUM, HIGH, CRITICAL"
            )
        return normalized

    @field_validator("source", "entity_type", "entity_id")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return value.strip()


class OperationalStateSnapshot(BaseModel):
    """Defensive snapshot of the current normalized operational state."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=0)
    last_sequence: int = Field(ge=-1)
    last_simulation_time_min: int | None = Field(default=None, ge=0)

    entities: dict[str, dict[str, dict[str, Any]]] = Field(default_factory=dict)
    active_disruptions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    recent_events: list[OperationalEvent] = Field(default_factory=list)

    running: bool = False
    stop_at_minute: int | None = Field(default=None, ge=0)
    done: bool = False
    last_updated_at: datetime | None = None
    source: str = "SIMULATED_OPERATIONAL_FEED"
    scenario_id: str = "mumbai_weather_crisis_v2"


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
    """Construct an operational event without embedding domain logic."""
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
