from __future__ import annotations


def apply_candidate_to_flight(flight, candidate: dict) -> None:
    flight.route = list(candidate["route"])
    flight.route_index = 0
    flight.edge_progress_min = 0.0
    if candidate.get("cruise_altitude_ft") is not None:
        flight.altitude_ft = float(candidate["cruise_altitude_ft"])
    if candidate.get("speed_kt") is not None:
        flight.speed_kt = float(candidate["speed_kt"])
    flight.status = "REROUTING"


def reset_target_to_candidate_start(flight, state, candidate: dict) -> None:
    start = candidate["route"][0]
    flight.route = list(candidate["route"])
    flight.route_index = 0
    flight.edge_progress_min = 0.0
    flight.position.lat = state.graph.nodes[start]["lat"]
    flight.position.lon = state.graph.nodes[start]["lon"]
