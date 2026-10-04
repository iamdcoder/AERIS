from app.engine.digital_twin.loaders import load_world
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
    assert by_id["ALT-A"] == ["W0", "W1", "W2", "W3", "W10", "W11", "W12", "BOM"]
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


def test_flight_id_change_preserves_route_definition():
    state = load_world()
    a = generate_candidate_routes(state.graph, "F102")
    b = generate_candidate_routes(state.graph, "F999")
    assert len(a) == len(b) == 5
    for candidate_a, candidate_b in zip(a, b):
        assert candidate_a["flight_id"] == "F102"
        assert candidate_b["flight_id"] == "F999"
        assert {key: value for key, value in candidate_a.items() if key != "flight_id"} == {
            key: value for key, value in candidate_b.items() if key != "flight_id"
        }

