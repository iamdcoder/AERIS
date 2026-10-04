from __future__ import annotations

from typing import Any

from .graph import route_distance_km, route_is_valid


SCENARIO_CANDIDATES: list[dict[str, Any]] = [
    {
        "candidate_id": "ALT-A",
        "intervention_type": "reroute",
        "strategy": "shortest_bypass",
        "route": ["W0", "W1", "W2", "W3", "W10", "W11", "W12", "BOM"],
        "cruise_altitude_ft": 32000,
        "speed_kt": 430,
        "timing_offset_min": 0,
        "hold_min": 0,
    },
    {
        "candidate_id": "ALT-B",
        "intervention_type": "reroute",
        "strategy": "fuel_efficient_south_east",
        "route": ["W0", "W1", "W4", "W5", "W6", "W8", "W11", "W12", "BOM"],
        "cruise_altitude_ft": 30000,
        "speed_kt": 430,
        "timing_offset_min": 0,
        "hold_min": 0,
    },
    {
        "candidate_id": "ALT-C",
        "intervention_type": "altitude_strategy",
        "strategy": "direct_high_level",
        "route": ["W0", "W4", "W5", "W10", "W11", "W12", "BOM"],
        "cruise_altitude_ft": 34000,
        "speed_kt": 435,
        "timing_offset_min": 0,
        "hold_min": 0,
    },
    {
        "candidate_id": "ALT-D",
        "intervention_type": "reroute",
        "strategy": "sector_diversion_resilient",
        "route": ["W0", "W4", "W5", "W7", "BOM"],
        "cruise_altitude_ft": 28000,
        "speed_kt": 420,
        "timing_offset_min": 0,
        "hold_min": 0,
    },
    {
        "candidate_id": "ALT-E",
        "intervention_type": "reroute",
        "strategy": "conservative_west_arc",
        "route": ["W0", "W1", "PNQ", "W7", "W9", "W8", "W11", "W12", "BOM"],
        "cruise_altitude_ft": 26000,
        "speed_kt": 410,
        "timing_offset_min": 0,
        "hold_min": 0,
    },
]


def generate_interventions(graph, flight_id: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for template in SCENARIO_CANDIDATES:
        valid, reason = route_is_valid(graph, template["route"])
        candidate = dict(template)
        candidate["flight_id"] = flight_id
        candidate["feasible"] = False
        candidate["route_valid"] = valid
        candidate["route_validation_error"] = reason
        candidate["added_distance_km"] = route_distance_km(graph, candidate["route"]) if valid else None
        candidates.append(candidate)
    return candidates
