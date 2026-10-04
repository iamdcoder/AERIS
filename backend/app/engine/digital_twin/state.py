from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from ...models.aircraft import Aircraft
from ...models.airport import Airport
from ...models.restriction import Restriction
from ...models.sector import Sector
from ...models.weather import WeatherCell


@dataclass
class WorldState:
    time_min: int
    aircraft: dict[str, Aircraft]
    sectors: dict[str, Sector]
    airports: dict[str, Airport]
    weather_cells: dict[str, WeatherCell]
    restrictions: dict[str, Restriction]
    graph: nx.DiGraph
    scenario: dict[str, Any]
    holding_flights: set[str] = field(default_factory=set)
    event_log: list[dict[str, Any]] = field(default_factory=list)
    approved_intervention: str | None = None

    def clone(self) -> "WorldState":
        return deepcopy(self)

    def snapshot(self) -> dict[str, Any]:
        return {
            "time_min": self.time_min,
            "aircraft": [a.model_dump() for a in self.aircraft.values()],
            "sectors": [s.model_dump() for s in self.sectors.values()],
            "airports": [a.model_dump() for a in self.airports.values()],
            "weather_cells": [w.model_dump() for w in self.weather_cells.values()],
            "restrictions": [r.model_dump() for r in self.restrictions.values()],
            "events": self.event_log[-10:],
        }
