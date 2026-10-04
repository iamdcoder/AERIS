from __future__ import annotations

from .interventions import generate_interventions


def generate_candidate_routes(graph, flight_id: str) -> list[dict]:
    """Scenario-aware deterministic candidate generator.

    We intentionally use five distinct intervention strategies for the flagship demo
    instead of returning five nearly identical k-shortest paths.
    """
    return generate_interventions(graph, flight_id)
