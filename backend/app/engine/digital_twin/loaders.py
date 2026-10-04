from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from ...models.aircraft import Aircraft, Position
from ...models.airport import Airport
from ...models.restriction import Restriction
from ...models.sector import Sector
from ...models.weather import WeatherCell
from .state import WorldState


ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = ROOT / "backend" / "data"
SCENARIO_DIR = ROOT / "scenarios"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_scenario(name: str = "mumbai_weather_crisis.json") -> dict:
    return _read_json(SCENARIO_DIR / name)


def load_graph() -> nx.DiGraph:
    raw = _read_json(DATA_DIR / "airway_graph.json")
    graph = nx.DiGraph()
    for node in raw["nodes"]:
        graph.add_node(node["id"], lat=node["lat"], lon=node["lon"])
    for edge in raw["edges"]:
        graph.add_edge(edge["from"], edge["to"])
    return graph


def _node_position(graph: nx.DiGraph, node_id: str) -> Position:
    data = graph.nodes[node_id]
    return Position(lat=data["lat"], lon=data["lon"])


def load_world(scenario_name: str = "mumbai_weather_crisis.json") -> WorldState:
    graph = load_graph()
    aircraft_raw = _read_json(DATA_DIR / "aircraft.json")
    sectors_raw = _read_json(DATA_DIR / "sectors.json")
    airports_raw = _read_json(DATA_DIR / "airports.json")
    weather_raw = _read_json(DATA_DIR / "weather.json")
    restrictions_raw = _read_json(DATA_DIR / "restrictions.json")
    scenario = load_scenario(scenario_name)

    airports: dict[str, Airport] = {}
    for item in airports_raw["airports"]:
        airports[item["id"]] = Airport(
            id=item["id"],
            name=item.get("name", ""),
            position=Position(lat=item["lat"], lon=item["lon"]),
            arrival_capacity=item["arrival_capacity"],
            departure_capacity=item["departure_capacity"],
            weather_status=item.get("weather_status", "NORMAL"),
            operational_status=item.get("operational_status", "NORMAL"),
        )

    sectors: dict[str, Sector] = {}
    for item in sectors_raw["sectors"]:
        sectors[item["id"]] = Sector(**item)

    weather_cells: dict[str, WeatherCell] = {}
    for item in weather_raw["weather_cells"]:
        weather_cells[item["id"]] = WeatherCell(**item)

    restrictions: dict[str, Restriction] = {}
    for item in restrictions_raw["restrictions"]:
        restrictions[item["id"]] = Restriction(**item)

    aircraft: dict[str, Aircraft] = {}
    target = aircraft_raw["target"]
    aircraft[target["id"]] = Aircraft(
        id=target["id"],
        callsign=target["callsign"],
        position=_node_position(graph, target["start_node"]),
        altitude_ft=target["altitude_ft"],
        speed_kt=target["speed_kt"],
        route=target["route"] if "route" in target else [target["start_node"], "BOM"],
        destination=target["destination"],
        fuel_remaining_min=target["fuel_remaining_min"],
        burn_rate_min_per_min=target["burn_rate_min_per_min"],
        performance_class=target.get("performance_class", "MEDIUM"),
        status=target.get("status", "AIRBORNE"),
        route_index=0,
        airline=target.get("airline", "SIM-AIR"),
        tail_number=target.get("tail_number", ""),
        original_route=list(target.get("route", [target["start_node"], "BOM"])),
    )

    count = int(aircraft_raw.get("count", 40))
    templates = aircraft_raw["background_templates"]
    for i in range(count - 1):
        t = templates[i % len(templates)]
        flight_id = f"{t['prefix']}-{i + 1:02d}"
        route = list(t["route"])
        route_index = (i // len(templates)) % max(1, min(2, len(route) - 1))
        start_node = route[route_index]
        aircraft[flight_id] = Aircraft(
            id=flight_id,
            callsign=f"{t['prefix']}{i + 1:02d}",
            position=_node_position(graph, start_node),
            altitude_ft=t["altitude_ft"],
            speed_kt=t["speed_kt"],
            route=route,
            destination=t["destination"],
            fuel_remaining_min=max(15.0, t["fuel_remaining_min"] - (i % 5)),
            burn_rate_min_per_min=t["burn_rate_min_per_min"],
            performance_class="A320",
            status="AIRBORNE",
            route_index=route_index,
            airline="SIM-AIR",
            tail_number=f"VT-S{i + 1:03d}",
            original_route=list(route),
        )

    # Every flight gets an initial planned travel estimate. The circular dependency
    # with the route graph is resolved in the simulator when the world is first used.
    state = WorldState(
        time_min=0,
        aircraft=aircraft,
        sectors=sectors,
        airports=airports,
        weather_cells=weather_cells,
        restrictions=restrictions,
        graph=graph,
        scenario=scenario,
    )
    return state
