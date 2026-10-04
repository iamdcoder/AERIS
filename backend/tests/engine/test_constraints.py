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
def test_flagship_restriction_failure_and_reanchored_conservative_fuel_at_19():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(19)
    candidates = generate_candidate_routes(sim.state.graph, "F102")
    results = {c["candidate_id"]: validate_candidate(sim.state, c) for c in candidates}
    assert results["ALT-C"]["feasible"] is False
    assert results["ALT-E"]["feasible"] is False
    assert results["ALT-E"]["constraint_results"]["fuel"]["feasible"] is False
    assert candidates[-1]["route"][0] == sim.state.aircraft["F102"].route[
        sim.state.aircraft["F102"].route_index
    ]
    assert results["ALT-A"]["feasible"] is True
    assert results["ALT-B"]["feasible"] is True
    assert results["ALT-D"]["feasible"] is True
    assert results["ALT-C"]["constraint_results"]["restriction"]["passed"] is False


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


# ===========================================================================
# TEMPORAL SECTOR CAPACITY (Parts 4 & 5)
# ===========================================================================

# TEST 21 — SECTOR RESULTS CONTAIN TEMPORAL TRAVERSAL WINDOWS
def test_capacity_sector_results_include_traversal_times():
    """capacity_check should expose entry_time_min and exit_time_min for each sector."""
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]
    result = capacity_check(state, route)
    for sid, sr in result["sectors"].items():
        assert "entry_time_min" in sr, f"sector {sid} missing entry_time_min"
        assert "exit_time_min" in sr, f"sector {sid} missing exit_time_min"
        assert sr["exit_time_min"] >= sr["entry_time_min"]


# TEST 22 — SECTOR RESULTS CONTAIN REMAINING HEADROOM
def test_capacity_sector_results_include_remaining_headroom():
    """capacity_check should expose remaining_headroom = capacity - candidate_projected."""
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]
    result = capacity_check(state, route)
    for sid, sr in result["sectors"].items():
        expected = sr["capacity"] - sr["candidate_projected_occupancy"]
        assert sr["remaining_headroom"] == expected, (
            f"sector {sid}: headroom {sr['remaining_headroom']} != expected {expected}"
        )


# TEST 23 — CAPACITY RESULT INCLUDES CURRENT AND FORECAST OCCUPANCY
def test_capacity_sector_results_include_current_and_forecast_occupancy():
    """capacity_check should expose current_occupancy and forecast_demand."""
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]
    result = capacity_check(state, route)
    for sid, sr in result["sectors"].items():
        assert "current_occupancy" in sr
        assert "forecast_demand" in sr
        assert isinstance(sr["current_occupancy"], int)
        assert isinstance(sr["forecast_demand"], int)


# TEST 24 — BOM ARRIVAL RESULT INCLUDES TIMING METADATA
def test_capacity_bom_result_includes_arrival_time_min():
    """When the candidate destination is BOM, result should include arrival_time_min."""
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]
    result = capacity_check(state, route)
    assert "arrival_time_min" in result["airport"]
    assert result["airport"]["arrival_time_min"] is not None
    assert result["airport"]["arrival_time_min"] > 0.0


# TEST 25 — BOM HARD REJECT ONLY ON CLOSED STATUS
def test_capacity_bom_hard_reject_only_when_closed():
    """capacity_check should only hard-fail BOM when operational_status is CLOSED."""
    state = load_world()
    # Normal state with many inbound should still pass.
    route = ["W0", "W4", "W5", "W7", "BOM"]
    result = capacity_check(state, route)
    assert result["airport"]["passed"] is True

    # CLOSED should cause a hard failure.
    state.airports["BOM"].operational_status = "CLOSED"
    result_closed = capacity_check(state, route)
    assert result_closed["airport"]["passed"] is False


# TEST 26 — BOM DEGRADED WINDOW METADATA
def test_capacity_bom_degraded_window_flagged_after_t8():
    """After BOM arrival capacity drops (t=8), result should flag degraded_window."""
    sim = DigitalTwinSimulator(load_world())
    sim.advance(8)
    assert sim.state.airports["BOM"].weather_status == "SEVERE_CONVECTIVE"

    route = ["W0", "W4", "W5", "W7", "BOM"]
    result = capacity_check(sim.state, route)
    assert result["airport"]["degraded_window"] is True
    assert "arrival_pressure_note" in result["airport"]


# TEST 27 — SPEED AFFECTS TRAVERSAL TIME (HIGHER SPEED → EARLIER ARRIVAL)
def test_capacity_higher_speed_yields_earlier_arrival():
    """A faster candidate should arrive at BOM earlier (lower arrival_time_min)."""
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]
    slow = capacity_check(state, route, speed_kt=300)
    fast = capacity_check(state, route, speed_kt=500)
    assert fast["airport"]["arrival_time_min"] < slow["airport"]["arrival_time_min"]


# TEST 28 — SECTOR TRAVERSAL TIME ORDERING IS MONOTONE
def test_capacity_sector_entry_times_increase_along_route():
    """Sectors encountered earlier along the route should have smaller entry_time_min values."""
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]
    result = capacity_check(state, route, speed_kt=430, start_time=0.0)
    # Collect entry times sorted by the position of the first sector-node in the route.
    route_pos = {node: i for i, node in enumerate(route)}
    sector_entries = []
    for sid, sr in result["sectors"].items():
        sector = state.sectors[sid]
        first_node_pos = min(route_pos[n] for n in route if n in sector.nodes)
        sector_entries.append((first_node_pos, sr["entry_time_min"]))
    sector_entries.sort()
    times = [t for _, t in sector_entries]
    assert times == sorted(times), f"Sector entry times not monotonically increasing: {times}"


# ===========================================================================
# CONFLICT SPATIAL SEPARATION (Part 6)
# ===========================================================================

# TEST 29 — CONFLICT EVIDENCE INCLUDES SPATIAL SEPARATION
def test_conflict_evidence_includes_estimated_spatial_separation_nm():
    """Conflict check should return estimated_spatial_separation_nm in each conflict record."""
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
    c = result["conflicts"][0]
    assert "estimated_spatial_separation_nm" in c
    assert isinstance(c["estimated_spatial_separation_nm"], float)
    assert c["estimated_spatial_separation_nm"] >= 0.0


# TEST 30 — CONFLICT EVIDENCE INCLUDES SEGMENT LABEL
def test_conflict_evidence_includes_segment_label():
    """Conflict check should include a 'segment' string identifying the conflicting edge."""
    state = load_world()
    target_flight = state.aircraft["F102"]
    candidate_route = ["W0", "W4", "W5", "W7", "BOM"]

    other = state.aircraft["AI2-01"]
    other.route = list(candidate_route)
    other.route_index = 0
    other.edge_progress_min = 0.0
    other.status = "AIRBORNE"
    other.speed_kt = target_flight.speed_kt

    result = conflict_check(state, "F102", candidate_route, target_flight.speed_kt)
    assert result["passed"] is False
    c = result["conflicts"][0]
    assert "segment" in c
    assert "->" in c["segment"]


# TEST 31 — CONFLICT EVIDENCE INCLUDES REQUIRED SEPARATION
def test_conflict_evidence_includes_required_separation_nm():
    """Each conflict record and the top-level result should include required_separation_nm."""
    state = load_world()
    target_flight = state.aircraft["F102"]
    candidate_route = ["W0", "W4", "W5", "W7", "BOM"]

    other = state.aircraft["AI2-01"]
    other.route = list(candidate_route)
    other.route_index = 0
    other.edge_progress_min = 0.0
    other.status = "AIRBORNE"
    other.speed_kt = target_flight.speed_kt

    result = conflict_check(state, "F102", candidate_route, target_flight.speed_kt)
    assert result["required_separation_nm"] == 5.0
    assert result["conflicts"][0]["required_separation_nm"] == 5.0


# TEST 32 — SAME-POSITION CONFLICT YIELDS NEAR-ZERO SPATIAL SEPARATION
def test_conflict_same_waypoint_zero_spatial_separation():
    """Aircraft at the exact same waypoint at the same time should have ~0.0 NM separation."""
    state = load_world()
    target_flight = state.aircraft["F102"]
    candidate_route = ["W0", "W4", "W5", "W7", "BOM"]

    other = state.aircraft["AI2-01"]
    other.route = list(candidate_route)
    other.route_index = 0
    other.edge_progress_min = 0.0
    other.status = "AIRBORNE"
    other.speed_kt = target_flight.speed_kt  # same speed → same waypoint at same time

    result = conflict_check(state, "F102", candidate_route, target_flight.speed_kt)
    c = result["conflicts"][0]
    # Same position, same speed → near-zero spatial separation.
    assert c["estimated_spatial_separation_nm"] == pytest.approx(0.0, abs=0.1)
