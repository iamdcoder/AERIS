from __future__ import annotations

from typing import Any

import networkx as nx

from .graph import route_distance_km, route_is_valid


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


def generate_shortest_bypass(
    graph: nx.DiGraph,
    flight_id: str,
) -> dict[str, Any]:
    """Propose the shortest bypass route intervention candidate (ALT-A)."""
    return _build_candidate(
        graph,
        flight_id,
        candidate_id="ALT-A",
        intervention_type="reroute",
        strategy="shortest_bypass",
        route=["W0", "W1", "W2", "W3", "W10", "W11", "W12", "BOM"],
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
    return _build_candidate(
        graph,
        flight_id,
        candidate_id="ALT-B",
        intervention_type="reroute",
        strategy="fuel_efficient_south_east",
        route=["W0", "W1", "W4", "W5", "W6", "W8", "W11", "W12", "BOM"],
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
    return _build_candidate(
        graph,
        flight_id,
        candidate_id="ALT-C",
        intervention_type="altitude_strategy",
        strategy="direct_high_level",
        route=["W0", "W4", "W5", "W10", "W11", "W12", "BOM"],
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
    return _build_candidate(
        graph,
        flight_id,
        candidate_id="ALT-D",
        intervention_type="reroute",
        strategy="sector_diversion_resilient",
        route=["W0", "W4", "W5", "W7", "BOM"],
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
    return _build_candidate(
        graph,
        flight_id,
        candidate_id="ALT-E",
        intervention_type="reroute",
        strategy="conservative_west_arc",
        route=["W0", "W1", "PNQ", "W7", "W9", "W8", "W11", "W12", "BOM"],
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

