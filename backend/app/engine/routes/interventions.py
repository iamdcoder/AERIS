from __future__ import annotations

from typing import Any

import networkx as nx

from .graph import route_distance_km, route_is_valid, shortest_route


def _build_candidate(
    graph: nx.DiGraph,
    flight_id: str,
    *,
    candidate_id: str,
    intervention_type: str,
    strategy: str,
    route: list[str],
    cruise_altitude_ft: int,
    speed_kt: int,
    timing_offset_min: int = 0,
    hold_min: int = 0,
) -> dict[str, Any]:
    """Build and enrich a route candidate dictionary with validity and distance metrics."""
    valid, reason = route_is_valid(graph, route)
    added_distance = route_distance_km(graph, route) if valid else None
    return {
        "candidate_id": candidate_id,
        "flight_id": flight_id,
        "intervention_type": intervention_type,
        "strategy": strategy,
        "route": list(route),
        "cruise_altitude_ft": cruise_altitude_ft,
        "speed_kt": speed_kt,
        "timing_offset_min": timing_offset_min,
        "hold_min": hold_min,
        "feasible": False,
        "route_valid": valid,
        "route_validation_error": reason,
        "added_distance_km": added_distance,
    }


def _decision_node(graph: nx.DiGraph, flight_id: str) -> str:
    aircraft_by_id = graph.graph.get("_aircraft_by_id", {})
    flight = aircraft_by_id.get(flight_id)
    if flight is None:
        raise ValueError(f"Unknown flight or missing live route state: {flight_id}")
    if not flight.route or flight.route_index >= len(flight.route):
        raise ValueError(f"Flight {flight_id} has no current route node")
    node = flight.route[flight.route_index]
    if node not in graph:
        raise ValueError(f"Current route node {node!r} for {flight_id} is not in the airway graph")
    return node


def _route_via_waypoints(
    graph: nx.DiGraph,
    start: str,
    destination: str,
    waypoints: list[str],
) -> list[str]:
    """Connect reachable strategy waypoints with valid shortest graph paths."""
    route = [start]
    current = start
    for waypoint in waypoints:
        if waypoint == current or waypoint in route or waypoint not in graph:
            continue
        if not nx.has_path(graph, current, waypoint):
            continue
        if not nx.has_path(graph, waypoint, destination):
            continue
        segment = shortest_route(graph, current, waypoint)
        route.extend(segment[1:])
        current = waypoint

    if current != destination:
        route.extend(shortest_route(graph, current, destination)[1:])
    return route


def _strategy_route(
    graph: nx.DiGraph,
    flight_id: str,
    *,
    waypoints: list[str] | None = None,
) -> tuple[nx.DiGraph, list[str]]:
    """Build a strategy continuation on a graph copy to avoid mutating the world."""
    working_graph = graph.copy()
    start = _decision_node(working_graph, flight_id)
    flight = working_graph.graph["_aircraft_by_id"][flight_id]
    destination = flight.destination
    if destination not in working_graph:
        raise ValueError(f"Unknown destination {destination!r} for flight {flight_id}")

    if waypoints is None:
        route = shortest_route(working_graph, start, destination)
    else:
        route = _route_via_waypoints(working_graph, start, destination, waypoints)
    return working_graph, route


def generate_shortest_bypass(
    graph: nx.DiGraph,
    flight_id: str,
) -> dict[str, Any]:
    """Propose the shortest graph continuation from the flight's current node (ALT-A)."""
    working_graph, route = _strategy_route(graph, flight_id)
    return _build_candidate(
        working_graph,
        flight_id,
        candidate_id="ALT-A",
        intervention_type="reroute",
        strategy="shortest_bypass",
        route=route,
        cruise_altitude_ft=32000,
        speed_kt=430,
        timing_offset_min=0,
        hold_min=0,
    )


def generate_fuel_efficient_route(
    graph: nx.DiGraph,
    flight_id: str,
) -> dict[str, Any]:
    """Propose the fuel-efficient south-east route intervention candidate (ALT-B)."""
    working_graph, route = _strategy_route(
        graph,
        flight_id,
        waypoints=["W1", "W4", "W5", "W6", "W8", "W11", "W12"],
    )
    return _build_candidate(
        working_graph,
        flight_id,
        candidate_id="ALT-B",
        intervention_type="reroute",
        strategy="fuel_efficient_south_east",
        route=route,
        cruise_altitude_ft=30000,
        speed_kt=430,
        timing_offset_min=0,
        hold_min=0,
    )


def generate_high_altitude_route(
    graph: nx.DiGraph,
    flight_id: str,
) -> dict[str, Any]:
    """Propose the direct high-level altitude strategy intervention candidate (ALT-C)."""
    working_graph, route = _strategy_route(
        graph,
        flight_id,
        waypoints=["W4", "W5", "W10", "W11", "W12"],
    )
    return _build_candidate(
        working_graph,
        flight_id,
        candidate_id="ALT-C",
        intervention_type="altitude_strategy",
        strategy="direct_high_level",
        route=route,
        cruise_altitude_ft=34000,
        speed_kt=435,
        timing_offset_min=0,
        hold_min=0,
    )


def generate_resilient_sector_diversion(
    graph: nx.DiGraph,
    flight_id: str,
) -> dict[str, Any]:
    """Propose the resilient sector diversion route intervention candidate (ALT-D)."""
    working_graph, route = _strategy_route(
        graph,
        flight_id,
        waypoints=["W4", "W5", "W7"],
    )
    return _build_candidate(
        working_graph,
        flight_id,
        candidate_id="ALT-D",
        intervention_type="reroute",
        strategy="sector_diversion_resilient",
        route=route,
        cruise_altitude_ft=28000,
        speed_kt=420,
        timing_offset_min=0,
        hold_min=0,
    )


def generate_conservative_route(
    graph: nx.DiGraph,
    flight_id: str,
) -> dict[str, Any]:
    """Propose the conservative west arc route intervention candidate (ALT-E)."""
    working_graph, route = _strategy_route(
        graph,
        flight_id,
        waypoints=["W1", "PNQ", "W7", "W9", "W8", "W11", "W12"],
    )
    return _build_candidate(
        working_graph,
        flight_id,
        candidate_id="ALT-E",
        intervention_type="reroute",
        strategy="conservative_west_arc",
        route=route,
        cruise_altitude_ft=26000,
        speed_kt=410,
        timing_offset_min=0,
        hold_min=0,
    )


def generate_interventions(graph: nx.DiGraph, flight_id: str) -> list[dict[str, Any]]:
    """Generate candidate routes using deterministic intervention strategies."""
    return [
        generate_shortest_bypass(graph, flight_id),
        generate_fuel_efficient_route(graph, flight_id),
        generate_high_altitude_route(graph, flight_id),
        generate_resilient_sector_diversion(graph, flight_id),
        generate_conservative_route(graph, flight_id),
    ]

