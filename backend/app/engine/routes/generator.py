from __future__ import annotations

from typing import Any

import networkx as nx

from .interventions import generate_interventions


def generate_candidate_routes(
    graph: nx.DiGraph,
    flight_id: str,
) -> list[dict[str, Any]]:
    """Scenario-aware candidate generator driving deterministic intervention strategies.

    This function generates deterministic intervention candidates.
    It does not validate operational constraints; validation happens later in constraints/validator.py.
    """
    return generate_interventions(graph, flight_id)

