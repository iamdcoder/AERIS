import pytest

from app.engine.constraints.capacity import capacity_check
from app.engine.constraints.conflict import conflict_check
from app.engine.constraints.fuel import fuel_feasibility
from app.engine.constraints.restriction import restriction_check
from app.engine.constraints.validator import validate_candidate
from app.engine.constraints.weather import weather_intersection
from app.engine.digital_twin.loaders import load_world
from app.engine.digital_twin.simulator import DigitalTwinSimulator
from app.engine.routes.generator import generate_candidate_routes
from app.engine.routes.graph import route_distance_km, route_is_valid


# TEST 1 — ROUTE VALIDATION: VALID ROUTE
def test_route_validation_accepts_valid_route():
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]
    valid, reason = route_is_valid(state.graph, route)
    assert valid is True
    assert reason is None


# TEST 2 — ROUTE VALIDATION: UNKNOWN WAYPOINT
def test_route_validation_rejects_unknown_waypoint():
    state = load_world()
    route = ["W0", "DOES_NOT_EXIST", "BOM"]
    valid, reason = route_is_valid(state.graph, route)
    assert valid is False
    assert reason is not None
    assert "Unknown waypoint" in reason


# TEST 3 — ROUTE VALIDATION: MISSING EDGE
def test_route_validation_rejects_missing_edge():
    state = load_world()
    route = ["W0", "W5", "BOM"]
    valid, reason = route_is_valid(state.graph, route)
    assert valid is False
    assert reason is not None
    assert "Missing airway edge" in reason


# TEST 4 — FUEL: FEASIBLE
def test_fuel_constraint_passes_with_sufficient_fuel():
    state = load_world()
    flight = state.aircraft["F102"]
    route = ["W0", "W4", "W5", "W7", "BOM"]
    result = fuel_feasibility(state, flight, route, speed_kt=flight.speed_kt)
    assert result["feasible"] is True
    assert result["reserve_margin_min"] >= 0
    assert result["required_reserve_min"] == 12.0


# TEST 5 — FUEL: INSUFFICIENT
def test_fuel_constraint_rejects_insufficient_fuel():
    state = load_world()
    flight = state.aircraft["F102"]
    flight.fuel_remaining_min = 0.0
    route = ["W0", "W4", "W5", "W7", "BOM"]
    result = fuel_feasibility(state, flight, route, speed_kt=flight.speed_kt)
    assert result["feasible"] is False
    assert result["violation_reason"] == "Insufficient fuel reserve for candidate route"
    assert result["reserve_margin_min"] < 0


# TEST 6 — FUEL: EXACT RESERVE BOUNDARY
def test_fuel_constraint_accepts_exact_reserve_boundary():
    state = load_world()
    flight = state.aircraft["F102"]
    route = ["W0", "W4", "W5", "W7", "BOM"]
    distance_km = route_distance_km(state.graph, route)
    speed_km_min = max(1.0, flight.speed_kt * 1.852 / 60.0)
    estimated_flight_min = (distance_km / speed_km_min) * 1.5
    flight.fuel_remaining_min = estimated_flight_min + 12.0 + 1e-8

    result = fuel_feasibility(state, flight, route, speed_kt=flight.speed_kt)
    assert result["feasible"] is True
    assert result["reserve_margin_min"] == pytest.approx(0.0, abs=1e-2)


# TEST 7 — WEATHER: NO INTERSECTION
def test_weather_constraint_passes_for_route_outside_weather():
    state = load_world()
    route = ["W0", "W4"]
    result = weather_intersection(state, route)
    assert result["intersects"] is False
    assert result["severity"] == "NONE"
    assert result["passed"] is True


# TEST 8 — WEATHER: INTERSECTION
def test_weather_constraint_detects_intersection():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(5)
    route = ["W0", "W4", "W5", "W10", "W11", "W12", "BOM"]
    result = weather_intersection(sim.state, route)
    assert result["intersects"] is True
    assert result["severity"] == "HIGH"
    assert result["passed"] is True
    assert result["bypass_implication"] == "RECOMMENDED"


# TEST 9 — CAPACITY: NORMAL
def test_capacity_constraint_passes_when_sector_has_room():
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]
    result = capacity_check(state, route)
    assert result["passed"] is True
    assert result["overloaded_sectors"] == []


# TEST 10 — CAPACITY: SECTOR OVERLOAD
def test_capacity_constraint_detects_sector_overload():
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]
    state.sectors["S4"].capacity = 1
    state.sectors["S4"].current_traffic = 1

    result = capacity_check(state, route)
    assert result["passed"] is False
    assert "S4" in result["overloaded_sectors"]
    assert "S4" in result["sectors"]
    assert result["sectors"]["S4"]["projected_occupancy"] > result["sectors"]["S4"]["capacity"]


# TEST 11 — AIRPORT CLOSED
def test_capacity_constraint_rejects_closed_destination_airport():
    state = load_world()
    state.airports["BOM"].operational_status = "CLOSED"
    route = ["W0", "W4", "W5", "W7", "BOM"]

    result = capacity_check(state, route)
    assert result["passed"] is False
    assert result["airport"]["passed"] is False
    assert result["airport"]["operational_status"] == "CLOSED"


# TEST 12 — RESTRICTION: OUTSIDE ACTIVE WINDOW
def test_restriction_constraint_passes_before_activation():
    state = load_world()
    route = ["W0", "W4", "W5", "W10", "W11", "W12", "BOM"]
    result = restriction_check(state, route, altitude_ft=34000)
    assert result["passed"] is True
    assert result["violations"] == []


# TEST 13 — RESTRICTION: ACTIVE + ALTITUDE VIOLATION
def test_restriction_constraint_rejects_high_altitude_route_at_t18():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(18)
    assert sim.state.time_min == 18
    assert sim.state.restrictions["R-MONSOON-01"].active is True

    route = ["W0", "W4", "W5", "W10", "W11", "W12", "BOM"]
    result = restriction_check(sim.state, route, altitude_ft=34000)
    assert result["passed"] is False
    assert len(result["violations"]) >= 1
    assert result["violations"][0]["restriction_id"] == "R-MONSOON-01"


# TEST 14 — RESTRICTION: SAME ROUTE BUT SAFE ALTITUDE
def test_restriction_constraint_allows_route_below_restricted_altitude():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(18)
    route = ["W0", "W4", "W5", "W10", "W11", "W12", "BOM"]
    result = restriction_check(sim.state, route, altitude_ft=30000)
    assert result["passed"] is True
    assert result["violations"] == []


# TEST 15 — CONFLICT: NO CONFLICT
def test_conflict_constraint_passes_when_no_new_conflict():
    sim = DigitalTwinSimulator(load_world())
    route = ["W0", "W4", "W5", "W7", "BOM"]
    speed_kt = sim.state.aircraft["F102"].speed_kt
    result = conflict_check(sim.state, "F102", route, speed_kt)
    assert result["passed"] is True
    assert result["conflicts"] == []


# TEST 16 — CONFLICT: SYNTHETIC DETERMINISTIC CONFLICT
def test_conflict_constraint_detects_same_waypoint_time_conflict():
    state = load_world()
    target_flight = state.aircraft["F102"]
    candidate_route = ["W0", "W4", "W5", "W7", "BOM"]
    candidate_speed = target_flight.speed_kt

    other = state.aircraft["AI2-01"]
    other.route = list(candidate_route)
    other.route_index = 0
    other.edge_progress_min = 0.0
    other.status = "AIRBORNE"
    other.speed_kt = candidate_speed

    result = conflict_check(state, "F102", candidate_route, candidate_speed)
    assert result["passed"] is False
    assert len(result["conflicts"]) >= 1

    c = result["conflicts"][0]
    assert "aircraft" in c
    assert "waypoint" in c
    assert "predicted_time_min" in c
    assert "time_separation_min" in c
    assert "severity" in c
    assert result["required_separation_nm"] == 5.0


# TEST 17 — VALIDATOR: FLAGSHIP HARD CONSTRAINT RESULT
def test_flagship_has_expected_two_hard_failures_at_19():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(19)
    candidates = generate_candidate_routes(sim.state.graph, "F102")
    results = {c["candidate_id"]: validate_candidate(sim.state, c) for c in candidates}
    assert results["ALT-C"]["feasible"] is False
    assert results["ALT-E"]["feasible"] is False
    assert results["ALT-A"]["feasible"] is True
    assert results["ALT-B"]["feasible"] is True
    assert results["ALT-D"]["feasible"] is True
    assert results["ALT-C"]["constraint_results"]["restriction"]["passed"] is False
    assert results["ALT-E"]["constraint_results"]["fuel"]["feasible"] is False


# TEST 18 — VALIDATOR RESULT STRUCTURE
def test_validator_returns_all_constraint_results():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(19)
    candidates = generate_candidate_routes(sim.state.graph, "F102")
    result = validate_candidate(sim.state, candidates[0])

    required_keys = {
        "candidate_id",
        "flight_id",
        "feasible",
        "constraint_results",
        "rejection_reasons",
        "weather_risk",
    }
    assert required_keys.issubset(result.keys())

    sub_results = result["constraint_results"]
    required_sub_keys = {"route", "weather", "fuel", "capacity", "conflict", "restriction"}
    assert required_sub_keys.issubset(sub_results.keys())


# TEST 19 — VALIDATOR COMBINES MULTIPLE FAILURES
def test_validator_reports_multiple_hard_failures():
    state = load_world()
    flight = state.aircraft["F102"]
    candidate_route = ["W0", "W4", "W5", "W7", "BOM"]
    candidate = {
        "candidate_id": "ALT-TEST",
        "flight_id": "F102",
        "route": candidate_route,
        "speed_kt": flight.speed_kt,
        "cruise_altitude_ft": flight.altitude_ft,
    }

    flight.fuel_remaining_min = 0.0
    state.sectors["S4"].capacity = 1
    state.sectors["S4"].current_traffic = 1

    result = validate_candidate(state, candidate)
    assert result["feasible"] is False
    assert len(result["rejection_reasons"]) >= 2
    assert result["constraint_results"]["fuel"]["feasible"] is False
    assert result["constraint_results"]["capacity"]["passed"] is False


# TEST 20 — WEATHER IS NOT AUTOMATICALLY A HARD FAILURE
def test_validator_keeps_severe_weather_as_risk_signal():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(5)
    candidates = generate_candidate_routes(sim.state.graph, "F102")
    found_high_weather = False
    for candidate in candidates:
        res = validate_candidate(sim.state, candidate)
        if res["constraint_results"]["weather"]["severity"] == "HIGH":
            found_high_weather = True
            assert res["constraint_results"]["weather"]["passed"] is True
            assert res["weather_risk"] == "HIGH"
            has_hard_failures = len(res["rejection_reasons"]) > 0
            assert res["feasible"] == (not has_hard_failures)
    assert found_high_weather is True
