from app.engine.digital_twin.loaders import load_world
from app.engine.digital_twin.simulator import DigitalTwinSimulator
from app.engine.routes.generator import generate_candidate_routes
from app.engine.routes.interventions import (
    generate_conservative_route,
    generate_fuel_efficient_route,
    generate_high_altitude_route,
    generate_resilient_sector_diversion,
    generate_shortest_bypass,
)


def test_five_candidates_generated():
    state = load_world()
    candidates = generate_candidate_routes(state.graph, "F102")
    assert len(candidates) == 5


def test_candidate_order():
    state = load_world()
    candidates = generate_candidate_routes(state.graph, "F102")
    assert [c["candidate_id"] for c in candidates] == ["ALT-A", "ALT-B", "ALT-C", "ALT-D", "ALT-E"]


def test_routes_are_distinct():
    state = load_world()
    candidates = generate_candidate_routes(state.graph, "F102")
    routes = [tuple(c["route"]) for c in candidates]
    assert len(set(routes)) == 5


def test_flagship_routes_are_valid():
    state = load_world()
    candidates = generate_candidate_routes(state.graph, "F102")
    assert all(c["route_valid"] for c in candidates)


def test_exact_routes():
    state = load_world()
    candidates = generate_candidate_routes(state.graph, "F102")
    by_id = {c["candidate_id"]: c["route"] for c in candidates}
    assert by_id["ALT-A"] == ["W0", "W1", "W2", "W3", "W10", "W11", "BOM"]
    assert by_id["ALT-B"] == ["W0", "W1", "W4", "W5", "W6", "W8", "W11", "W12", "BOM"]
    assert by_id["ALT-C"] == ["W0", "W4", "W5", "W10", "W11", "W12", "BOM"]
    assert by_id["ALT-D"] == ["W0", "W4", "W5", "W7", "BOM"]
    assert by_id["ALT-E"] == ["W0", "W1", "PNQ", "W7", "W9", "W8", "W11", "W12", "BOM"]


def test_flagship_candidate_configuration():
    state = load_world()
    candidates = generate_candidate_routes(state.graph, "F102")
    expected = {
        "ALT-A": ("reroute", "shortest_bypass", 32000, 430),
        "ALT-B": ("reroute", "fuel_efficient_south_east", 30000, 430),
        "ALT-C": ("altitude_strategy", "direct_high_level", 34000, 435),
        "ALT-D": ("reroute", "sector_diversion_resilient", 28000, 420),
        "ALT-E": ("reroute", "conservative_west_arc", 26000, 410),
    }

    for candidate in candidates:
        intervention_type, strategy, altitude, speed = expected[candidate["candidate_id"]]
        assert candidate["intervention_type"] == intervention_type
        assert candidate["strategy"] == strategy
        assert candidate["cruise_altitude_ft"] == altitude
        assert candidate["speed_kt"] == speed
        assert candidate["timing_offset_min"] == 0
        assert candidate["hold_min"] == 0


def test_candidate_fields():
    state = load_world()
    candidates = generate_candidate_routes(state.graph, "F102")
    expected_fields = {
        "candidate_id",
        "flight_id",
        "intervention_type",
        "strategy",
        "route",
        "cruise_altitude_ft",
        "speed_kt",
        "timing_offset_min",
        "hold_min",
        "feasible",
        "route_valid",
        "route_validation_error",
        "added_distance_km",
    }
    for candidate in candidates:
        assert expected_fields.issubset(candidate.keys())


def test_individual_strategy_functions():
    state = load_world()

    c_a = generate_shortest_bypass(state.graph, "F102")
    assert c_a["candidate_id"] == "ALT-A"
    assert c_a["flight_id"] == "F102"
    assert c_a["strategy"] == "shortest_bypass"

    c_b = generate_fuel_efficient_route(state.graph, "F102")
    assert c_b["candidate_id"] == "ALT-B"
    assert c_b["flight_id"] == "F102"
    assert c_b["strategy"] == "fuel_efficient_south_east"

    c_c = generate_high_altitude_route(state.graph, "F102")
    assert c_c["candidate_id"] == "ALT-C"
    assert c_c["flight_id"] == "F102"
    assert c_c["strategy"] == "direct_high_level"

    c_d = generate_resilient_sector_diversion(state.graph, "F102")
    assert c_d["candidate_id"] == "ALT-D"
    assert c_d["flight_id"] == "F102"
    assert c_d["strategy"] == "sector_diversion_resilient"

    c_e = generate_conservative_route(state.graph, "F102")
    assert c_e["candidate_id"] == "ALT-E"
    assert c_e["flight_id"] == "F102"
    assert c_e["strategy"] == "conservative_west_arc"


def test_candidate_strategy_identity_is_generic_across_flights():
    state = load_world()
    candidates = generate_candidate_routes(state.graph, "AI2-01")
    assert len(candidates) == 5
    expected_node = state.aircraft["AI2-01"].route[0]
    for candidate in candidates:
        assert candidate["flight_id"] == "AI2-01"
        assert candidate["route"][0] == expected_node
        assert candidate["route_valid"] is True

    flagship_candidates = generate_candidate_routes(state.graph, "F102")
    for candidate_a, candidate_b in zip(flagship_candidates, candidates):
        assert candidate_b["flight_id"] == "AI2-01"
        assert candidate_a["candidate_id"] == candidate_b["candidate_id"]
        assert candidate_a["intervention_type"] == candidate_b["intervention_type"]
        assert candidate_a["strategy"] == candidate_b["strategy"]
        assert candidate_a["cruise_altitude_ft"] == candidate_b["cruise_altitude_ft"]
        assert candidate_a["speed_kt"] == candidate_b["speed_kt"]
        assert candidate_a["timing_offset_min"] == candidate_b["timing_offset_min"]
        assert candidate_a["hold_min"] == candidate_b["hold_min"]


def test_candidate_generation_does_not_mutate_world_or_graph():
    state = load_world()
    before_flight = state.aircraft["F102"].model_dump()
    before_edges = [
        (source, target, dict(data))
        for source, target, data in state.graph.edges(data=True)
    ]
    before_graph_metadata = dict(state.graph.graph)

    generate_candidate_routes(state.graph, "F102")

    assert state.aircraft["F102"].model_dump() == before_flight
    assert list(state.graph.edges(data=True)) == before_edges
    assert state.graph.graph == before_graph_metadata


def test_candidate_routes_follow_current_route_index_after_advancing_world():
    state = load_world()
    simulator = DigitalTwinSimulator(state)
    flight = state.aircraft["AI2-01"]
    original_node = flight.route[flight.route_index]

    for _ in range(20):
        simulator.tick()
        if flight.route[flight.route_index] != original_node:
            break

    current_node = flight.route[flight.route_index]
    assert current_node != original_node
    candidates = generate_candidate_routes(state.graph, flight.id)

    assert all(candidate["route"][0] == current_node for candidate in candidates)
    assert all(candidate["route_valid"] for candidate in candidates)

