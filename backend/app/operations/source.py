"""Operational-data source interfaces.

External authorized aviation adapters and the deterministic replay should publish
the same normalized :class:`OperationalEvent` contract. This module intentionally
contains no network client implementation.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .events import OperationalEvent, OperationalStateSnapshot


@runtime_checkable
class OperationalEventSource(Protocol):
    """Minimal interface required by an AERIS operational data source."""

    def snapshot(self) -> OperationalStateSnapshot:
        ...

    def events(self, limit: int = 20) -> list[OperationalEvent]:
        ...

    def reset(self) -> OperationalStateSnapshot:
        ...

    def start(self) -> OperationalStateSnapshot:
        ...

    def stop(self) -> OperationalStateSnapshot:
        ...
