from __future__ import annotations

from math import cos, radians
from typing import Any

from shapely.geometry import Point, Polygon

from ...models.airport import Airport
from ...models.weather import WeatherCell
from .loaders import load_world
from .state import WorldState
from ..routes.graph import haversine_km, route_distance_km


SIM_TIME_SCALE = 1.5


class DigitalTwinSimulator:
    """Deterministic one-minute-step operational simulator."""

    def __init__(self, state: WorldState):
        self.state = state
        self._initialize_plans()

    @classmethod
    def flagship(cls) -> "DigitalTwinSimulator":
        return cls(load_world())

    def _initialize_plans(self) -> None:
        for aircraft in self.state.aircraft.values():
            remaining = aircraft.route[aircraft.route_index :]
            if len(remaining) >= 2:
                distance = route_distance_km(self.state.graph, remaining)
                aircraft.planned_travel_time_min = distance / max(1.0, aircraft.speed_kt * 1.852 / 60.0)
            else:
                aircraft.planned_travel_time_min = 0.0

    def _apply_event(self, event: dict[str, Any]) -> None:
        name = event["event"]
        payload = event.get("payload", {})
        self.state.event_log.append({"t": self.state.time_min, "event": name, "payload": payload})

        if name == "convective_weather_develops_near_BOM":
            weather_id = payload.get("weather_id")
            if weather_id is not None:
                cell = self.state.weather_cells[weather_id]
            else:
                cell = next(
                    (item for item in self.state.weather_cells.values() if item.active),
                    None,
                )
                if cell is None:
                    raise ValueError("Weather development event has no active weather cell")
            coords = cell.geometry["coordinates"][0]
            lons = [p[0] for p in coords]
            lats = [p[1] for p in coords]
            cx, cy = sum(lons) / len(lons), sum(lats) / len(lats)
            factor = float(payload.get("expand_factor", 1.35))
            expanded = []
            for lon, lat in coords:
                expanded.append([cx + (lon - cx) * factor, cy + (lat - cy) * factor])
            expanded.append(expanded[0])
            cell.geometry = {"type": "Polygon", "coordinates": [expanded]}
            cell.intensity = payload.get("intensity", "HIGH")
            cell.uncertainty = 0.25

        elif name.endswith("_arrival_capacity_drops") or name == "airport_arrival_capacity_drops":
            airport_id = payload.get("airport_id")
            if airport_id is None and name != "airport_arrival_capacity_drops":
                airport_id = name.removesuffix("_arrival_capacity_drops")
            if airport_id not in self.state.airports:
                raise ValueError(f"Arrival-capacity event references unknown airport: {airport_id}")
            airport = self.state.airports[airport_id]
            airport.arrival_capacity = int(payload["arrival_capacity"])
            airport.weather_status = payload.get("weather_status", "SEVERE_CONVECTIVE")
        elif name == "holding_begins":
            affected = payload.get("affected_flights", [])
            self.state.holding_flights.update(affected)
            self.state.holding_extra_fuel_burn = float(payload.get("extra_fuel_burn_per_min", 0.75))
            for fid in affected:
                if fid in self.state.aircraft:
                    f = self.state.aircraft[fid]
                    if f.status in ("AIRBORNE", "DEGRADED"):
                        f._pre_holding_status = f.status
                        f.status = "HOLDING"

        elif name == "holding_ends":
            affected = payload.get("affected_flights", list(self.state.holding_flights))
            for fid in list(affected):
                self.state.holding_flights.discard(fid)
                if fid in self.state.aircraft:
                    f = self.state.aircraft[fid]
                    if f.status == "HOLDING":
                        f.status = getattr(f, "_pre_holding_status", "AIRBORNE")

        elif name == "bypass_sector_approaches_capacity":
            sector = self.state.sectors[payload["sector_id"]]
            sector.capacity = int(payload["capacity"])
            sector.forecast_traffic = max(sector.forecast_traffic, sector.capacity - 1)

        elif name.endswith("_operational_degradation") or name == "target_operational_degradation":
            flight_id = payload.get("flight_id", self.state.scenario.get("target_flight_id"))
            if flight_id not in self.state.aircraft:
                raise ValueError(f"Degradation event references unknown flight: {flight_id}")
            flight = self.state.aircraft[flight_id]
            flight.status = payload.get("status", "DEGRADED")
            if "fuel_remaining_min" in payload:
                flight.fuel_remaining_min = float(payload["fuel_remaining_min"])

        elif name == "activate_temporary_restriction":
            rid = payload["restriction_id"]
            self.state.restrictions[rid].active = True

        elif name == "dispatcher_approval":
            # The scenario event is a timeline marker; approval is applied by
            # the public facade after an explicit caller decision.
            pass

    def _events_at(self, t: int) -> list[dict[str, Any]]:
        return [event for event in self.state.scenario.get("events", []) if int(event.get("t", -1)) == t]

    def _airport_arrival_pressure(self) -> None:
        for airport in self.state.airports.values():
            normal_capacity = float(
                getattr(airport, "normal_arrival_capacity", airport.arrival_capacity)
            )
            if airport.arrival_capacity >= normal_capacity:
                continue
            active_inbound = [
                flight
                for flight in self.state.aircraft.values()
                if flight.destination == airport.id
                and flight.status not in {"LANDED", "CANCELLED"}
            ]
            if len(active_inbound) > airport.arrival_capacity:
                for flight in active_inbound:
                    if flight.status != "HOLDING":
                        flight.delay_min += 0.25

    def _move_aircraft_one_minute(self, flight) -> None:
        if flight.status in {"LANDED", "CANCELLED"} or flight.route_index >= len(flight.route) - 1:
            if flight.route and flight.route[-1] == flight.destination:
                flight.status = "LANDED"
            return

        target_flight_id = self.state.scenario.get("target_flight_id")
        approval_times = [
            int(event["t"])
            for event in self.state.scenario.get("events", [])
            if event.get("event") == "dispatcher_approval" and "t" in event
        ]
        decision_deadline = min(approval_times) if approval_times else -1
        # Hold the scenario's target until its scheduled approval event, without
        # coupling the simulator to a particular flagship flight identifier.
        if (
            flight.id == target_flight_id
            and flight.status == "DEGRADED"
            and self.state.time_min < decision_deadline
            and self.state.approved_intervention is None
        ):
            flight.fuel_remaining_min = max(0.0, flight.fuel_remaining_min - flight.burn_rate_min_per_min)
            flight.delay_min += 0.60
            return

        # Explicit holding logic: holding aircraft halt route progression, burn configured extra fuel, and accumulate delay.
        if flight.status == "HOLDING" or flight.id in self.state.holding_flights:
            flight.status = "HOLDING"
            extra_burn = getattr(self.state, "holding_extra_fuel_burn", 0.75)
            burn = flight.burn_rate_min_per_min + extra_burn
            flight.fuel_remaining_min = max(0.0, flight.fuel_remaining_min - burn)
            flight.delay_min += 1.0
            return

        # 1 simulation minute advances a proportional fraction of the current edge.
        current = flight.route[flight.route_index]
        nxt = flight.route[flight.route_index + 1]
        a = self.state.graph.nodes[current]
        b = self.state.graph.nodes[nxt]
        edge_km = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
        speed_km_min = max(2.0, flight.speed_kt * 1.852 / 60.0)
        edge_time = (edge_km / speed_km_min) * SIM_TIME_SCALE
        flight.edge_progress_min += 1.0

        if flight.edge_progress_min >= edge_time:
            flight.edge_progress_min -= edge_time
            flight.route_index += 1
            node = flight.route[flight.route_index]
            flight.position.lat = self.state.graph.nodes[node]["lat"]
            flight.position.lon = self.state.graph.nodes[node]["lon"]
        else:
            fraction = flight.edge_progress_min / edge_time
            flight.position.lat = a["lat"] + (b["lat"] - a["lat"]) * fraction
            flight.position.lon = a["lon"] + (b["lon"] - a["lon"]) * fraction

        burn = flight.burn_rate_min_per_min
        flight.fuel_remaining_min = max(0.0, flight.fuel_remaining_min - burn)

    def _move_weather_one_minute(self) -> None:
        for cell in self.state.weather_cells.values():
            if not cell.active:
                continue
            coords = cell.geometry["coordinates"][0]
            dlat = float(cell.movement.get("lat_per_min", 0.0))
            dlon = float(cell.movement.get("lon_per_min", 0.0))
            shifted = [[lon + dlon, lat + dlat] for lon, lat in coords]
            cell.geometry = {"type": "Polygon", "coordinates": [shifted]}

    def _recompute_sector_traffic(self) -> None:
        for sector in self.state.sectors.values():
            sector.current_traffic = 0

        for flight in self.state.aircraft.values():
            if flight.status in {"LANDED", "CANCELLED"}:
                continue
            if not flight.route or flight.route_index >= len(flight.route):
                continue
            current_node = flight.route[flight.route_index]
            for sector in self.state.sectors.values():
                if current_node in sector.nodes:
                    sector.current_traffic += 1
                    break

        for sector in self.state.sectors.values():
            sector.utilization_pct = round((sector.current_traffic / max(1, sector.capacity)) * 100, 1)

    def _airport_arrival_pressure(self) -> None:
        bom = self.state.airports.get("BOM")
        if not bom:
            return
        active_inbound = [
            flight
            for flight in self.state.aircraft.values()
            if flight.destination == "BOM"
            and flight.status not in {"LANDED", "CANCELLED"}
        ]
        inbound = len(active_inbound)
        # The capacity is an hourly-ish abstraction represented as per active wave pressure.
        if self.state.time_min >= 8 and inbound > bom.arrival_capacity:
            for f in active_inbound:
                if f.status != "HOLDING":
                    f.delay_min += 0.25

    def tick(self, apply_events: bool = True) -> WorldState:
        if apply_events:
            for event in self._events_at(self.state.time_min + 1):
                self._apply_event(event)
        self.state.time_min += 1
        self._move_weather_one_minute()
        for flight in self.state.aircraft.values():
            self._move_aircraft_one_minute(flight)
        self._airport_arrival_pressure()
        self._recompute_sector_traffic()
        return self.state

    def advance(self, minutes: int) -> WorldState:
        for _ in range(minutes):
            self.tick()
        return self.state
