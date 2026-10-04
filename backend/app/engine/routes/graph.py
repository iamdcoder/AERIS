from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Iterable

import networkx as nx


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * asin(sqrt(a))


def add_edge_distances(graph: nx.DiGraph) -> nx.DiGraph:
    for u, v in graph.edges:
        a, b = graph.nodes[u], graph.nodes[v]
        graph[u][v]["distance_km"] = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    return graph


def route_distance_km(graph: nx.DiGraph, route: Iterable[str]) -> float:
    route = list(route)
    total = 0.0
    for u, v in zip(route, route[1:]):
        if not graph.has_edge(u, v):
            raise ValueError(f"Route contains missing edge: {u}->{v}")
        if "distance_km" not in graph[u][v]:
            a, b = graph.nodes[u], graph.nodes[v]
            graph[u][v]["distance_km"] = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
        total += float(graph[u][v]["distance_km"])
    return round(total, 2)


def shortest_route(graph: nx.DiGraph, start: str, destination: str) -> list[str]:
    add_edge_distances(graph)
    return nx.shortest_path(graph, start, destination, weight="distance_km")


def route_is_valid(graph: nx.DiGraph, route: list[str]) -> tuple[bool, str | None]:
    if len(route) < 2:
        return False, "Route must contain at least two nodes"
    if any(node not in graph for node in route):
        missing = next(node for node in route if node not in graph)
        return False, f"Unknown waypoint: {missing}"
    for u, v in zip(route, route[1:]):
        if not graph.has_edge(u, v):
            return False, f"Missing airway edge: {u}->{v}"
    return True, None
