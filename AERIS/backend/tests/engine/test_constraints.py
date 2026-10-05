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


def test_low_altitude_fuel_penalty_comes_from_aircraft_profile():
    state = load_world()
    flight = state.aircraft["F102"]
    route = ["W0", "W4", "W5", "W7", "BOM"]

    low = fuel_feasibility(state, flight, route, speed_kt=430, cruise_altitude_ft=26000)
    high = fuel_feasibility(state, flight, route, speed_kt=430, cruise_altitude_ft=30000)
    assert low["estimated_flight_time_min"] - high["estimated_flight_time_min"] == pytest.approx(
        flight.low_altitude_fuel_penalty_min
    )


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


def test_bom_capacity_pressure_counts_holding_inbound_flights():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(10)
    route = ["W0", "W4", "W5", "W7", "BOM"]

    expected_inbound = sum(
        1
        for flight in sim.state.aircraft.values()
        if flight.destination == "BOM" and flight.status not in {"LANDED", "CANCELLED"}
    )
    result = capacity_check(sim.state, route)

    assert expected_inbound >= len(sim.state.holding_flights)
    assert result["airport"]["inbound_count"] == expected_inbound
    assert result["airport"]["projected_arrival_pressure"] == expected_inbound + 1


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


# ===========================================================================
# TASK 2 — CAPACITY MUST CAUSE REAL OUTCOMES
# ===========================================================================

def test_sector_capacity_reduction_changes_feasibility_and_restoring_restores_feasibility():
    """Lowering sector capacity below projected demand causes failure; restoring capacity passes."""
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]

    # Original state: passes with headroom
    original = capacity_check(state, route)
    assert original["passed"] is True

    # Constrain sector S4 capacity
    orig_cap = state.sectors["S4"].capacity
    state.sectors["S4"].capacity = 0
    constrained = capacity_check(state, route)
    assert constrained["passed"] is False
    assert "S4" in constrained["overloaded_sectors"]

    # Restore capacity
    state.sectors["S4"].capacity = orig_cap
    restored = capacity_check(state, route)
    assert restored["passed"] is True
    assert restored["overloaded_sectors"] == []


def test_sector_capacity_reduction_increases_network_delay_and_restoring_restores_delay():
    """Lowering sector capacity increases network delay; restoring capacity restores lower delay."""
    from app.engine.simulation.network import simulate_candidate

    state = load_world()
    candidate = {
        "candidate_id": "ALT-TEST-CAP",
        "flight_id": "F102",
        "route": ["W0", "W4", "W5", "W7", "BOM"],
        "speed_kt": 430,
        "cruise_altitude_ft": 32000,
    }

    base_sim = simulate_candidate(state, candidate)
    base_delay = base_sim["candidate_total_delay_min"]

    # Severely restrict sector capacity for traversed sector S4
    orig_cap = state.sectors["S4"].capacity
    state.sectors["S4"].capacity = 1
    restricted_sim = simulate_candidate(state, candidate)
    restricted_delay = restricted_sim["candidate_total_delay_min"]

    assert restricted_delay > base_delay

    # Restore capacity
    state.sectors["S4"].capacity = orig_cap
    restored_sim = simulate_candidate(state, candidate)
    assert restored_sim["candidate_total_delay_min"] == pytest.approx(base_delay)


def test_airport_closed_changes_feasibility_and_reopening_restores_feasibility():
    """Closing destination airport causes hard failure; reopening restores feasibility."""
    state = load_world()
    route = ["W0", "W4", "W5", "W7", "BOM"]

    assert capacity_check(state, route)["passed"] is True

    # Close BOM
    state.airports["BOM"].operational_status = "CLOSED"
    closed_check = capacity_check(state, route)
    assert closed_check["passed"] is False
    assert closed_check["airport"]["passed"] is False

    # Reopen BOM
    state.airports["BOM"].operational_status = "NORMAL"
    reopened_check = capacity_check(state, route)
    assert reopened_check["passed"] is True
    assert reopened_check["airport"]["passed"] is True


def test_airport_arrival_capacity_reduction_increases_network_delay_and_restoring_restores_delay():
    """Lowering airport arrival capacity causes arrival congestion delay; restoring restores lower delay."""
    from app.engine.simulation.network import simulate_candidate

    state = load_world()
    candidate = {
        "candidate_id": "ALT-TEST-AIR",
        "flight_id": "F102",
        "route": ["W0", "W4", "W5", "W7", "BOM"],
        "speed_kt": 430,
        "cruise_altitude_ft": 32000,
    }

    orig_capacity = state.airports["BOM"].arrival_capacity
    state.time_min = 10

    # Normal capacity
    normal_sim = simulate_candidate(state, candidate)

    # Restrict arrival capacity severely
    state.airports["BOM"].arrival_capacity = 2
    restricted_sim = simulate_candidate(state, candidate)
    assert restricted_sim["candidate_total_delay_min"] > normal_sim["candidate_total_delay_min"]

    # Restore arrival capacity
    state.airports["BOM"].arrival_capacity = orig_capacity
    restored_sim = simulate_candidate(state, candidate)
    assert restored_sim["candidate_total_delay_min"] == pytest.approx(normal_sim["candidate_total_delay_min"])


# ===========================================================================
# TASK 3 — CONFLICT DETECTION
# ===========================================================================

def test_conflict_aircraft_already_ahead_on_same_route_passes():
    """A candidate arriving at a waypoint after traffic has already passed does not conflict."""
    state = load_world()
    target_flight = state.aircraft["F102"]
    candidate_route = ["W0", "W4", "W5", "W7", "BOM"]

    other = state.aircraft["AI2-01"]
    other.route = list(candidate_route)
    # The traffic flight has already reached W4; F102 must still traverse W0->W4.
    other.route_index = 1
    other.edge_progress_min = 0.0
    other.status = "AIRBORNE"
    state.aircraft["AI2-01"].speed_kt = target_flight.speed_kt

    result = conflict_check(state, "F102", candidate_route, target_flight.speed_kt)
    assert result["passed"] is True
    assert result["conflicts"] == []


def test_conflict_nearby_spatially_separated_traffic_passes():
    """Traffic on parallel routes > 5.0 NM apart should not produce a false conflict."""
    state = load_world()
    target_flight = state.aircraft["F102"]
    route_a = ["W0", "W4", "W5", "W7", "BOM"]
    route_b = ["W1", "W2", "W3", "W10", "W11", "BOM"]
    assert route_is_valid(state.graph, route_b) == (True, None)

    other = state.aircraft["AI2-01"]
    other.route = list(route_b)
    other.route_index = 0
    other.status = "AIRBORNE"

    result = conflict_check(state, "F102", route_a, target_flight.speed_kt)
    assert result["passed"] is True
    assert result["conflicts"] == []


def test_conflict_candidate_introduces_conflict_causes_validator_rejection():
    """A candidate route that introduces a conflict causes validate_candidate to return feasible: False."""
    state = load_world()
    target_flight = state.aircraft["F102"]
    candidate_route = ["W0", "W4", "W5", "W7", "BOM"]

    other = state.aircraft["AI2-01"]
    other.route = list(candidate_route)
    other.route_index = 0
    other.edge_progress_min = 0.0
    other.status = "AIRBORNE"
    other.speed_kt = target_flight.speed_kt

    candidate = {
        "candidate_id": "ALT-CONFLICT",
        "flight_id": "F102",
        "route": candidate_route,
        "speed_kt": target_flight.speed_kt,
        "cruise_altitude_ft": target_flight.altitude_ft,
    }

    res = validate_candidate(state, candidate)
    assert res["feasible"] is False
    assert any("conflict" in r.lower() for r in res["rejection_reasons"])


def test_conflict_detection_repeatability():
    """Calling conflict_check twice on identical state produces identical output."""
    state = load_world()
    target_flight = state.aircraft["F102"]
    candidate_route = ["W0", "W4", "W5", "W7", "BOM"]

    r1 = conflict_check(state, "F102", candidate_route, target_flight.speed_kt)
    r2 = conflict_check(state, "F102", candidate_route, target_flight.speed_kt)
    assert r1 == r2


# ===========================================================================
# TASK 4 — AIRCRAFT PERFORMANCE
# ===========================================================================

def test_performance_normal_aircraft_within_envelope_passes():
    """Normal aircraft operating at FL350 and 430 kt passes performance check."""
    from app.engine.constraints.performance import performance_check

    state = load_world()
    flight = state.aircraft["F102"]
    flight.status = "AIRBORNE"

    res = performance_check(state, flight, cruise_altitude_ft=35000, speed_kt=430)
    assert res["passed"] is True
    assert res["violation_reason"] is None


def test_performance_normal_aircraft_beyond_altitude_envelope_fails():
    """Normal aircraft attempting cruise at FL410 (> 39,000 ft limit) fails performance check."""
    from app.engine.constraints.performance import performance_check

    state = load_world()
    flight = state.aircraft["F102"]
    flight.status = "AIRBORNE"

    res = performance_check(state, flight, cruise_altitude_ft=41000, speed_kt=430)
    assert res["passed"] is False
    assert "exceeds maximum performance envelope" in res["violation_reason"]


def test_performance_degraded_aircraft_at_normal_altitude_fails():
    """DEGRADED aircraft attempting FL350 (allowed normally, but > 33,000 ft degraded ceiling) fails."""
    from app.engine.constraints.performance import performance_check

    state = load_world()
    flight = state.aircraft["F102"]
    flight.status = "DEGRADED"

    res = performance_check(state, flight, cruise_altitude_ft=35000, speed_kt=430)
    assert res["passed"] is False
    assert "33000" in res["violation_reason"]


def test_performance_excessive_speed_fails():
    """Candidate with speed 500 kt (> 460 kt limit) fails performance check."""
    from app.engine.constraints.performance import performance_check

    state = load_world()
    flight = state.aircraft["F102"]
    flight.status = "AIRBORNE"

    res = performance_check(state, flight, cruise_altitude_ft=35000, speed_kt=500)
    assert res["passed"] is False
    assert "exceeds maximum performance speed" in res["violation_reason"]


def test_performance_check_repeatability():
    """Calling performance_check twice yields identical results."""
    from app.engine.constraints.performance import performance_check

    state = load_world()
    flight = state.aircraft["F102"]

    res1 = performance_check(state, flight, cruise_altitude_ft=34000, speed_kt=430)
    res2 = performance_check(state, flight, cruise_altitude_ft=34000, speed_kt=430)
    assert res1 == res2


# ===========================================================================
# TASK 6 — EXPLICIT FAILURE-MODE REGRESSION TESTS
# ===========================================================================

def test_failure_mode_1_no_feasible_route():
    """Failure Mode 1: Route with invalid/disconnected waypoint causes candidate rejection."""
    state = load_world()
    candidate = {
        "candidate_id": "ALT-FAIL-ROUTE",
        "flight_id": "F102",
        "route": ["W0", "INVALID_WAYPOINT", "BOM"],
        "speed_kt": 430,
        "cruise_altitude_ft": 32000,
    }

    initial_state_snap = state.clone()
    res1 = validate_candidate(state, candidate)
    assert res1["feasible"] is False
    assert any("Unknown waypoint" in r for r in res1["rejection_reasons"])
    assert state.time_min == initial_state_snap.time_min

    res2 = validate_candidate(state, candidate)
    assert res1 == res2

def test_failure_mode_2_insufficient_fuel():
    """Failure Mode 2: Flight with insufficient fuel for route + 12 min reserve causes rejection."""
    state = load_world()
    flight = state.aircraft["F102"]
    flight.fuel_remaining_min = 5.0

    candidate = {
        "candidate_id": "ALT-FAIL-FUEL",
        "flight_id": "F102",
        "route": ["W0", "W4", "W5", "W7", "BOM"],
        "speed_kt": flight.speed_kt,
        "cruise_altitude_ft": flight.altitude_ft,
    }

    res1 = validate_candidate(state, candidate)
    assert res1["feasible"] is False
    assert "Insufficient fuel reserve for candidate route" in res1["rejection_reasons"]

    res2 = validate_candidate(state, candidate)
    assert res1 == res2


def test_failure_mode_3_restricted_airspace():
    """Failure Mode 3: Candidate traversing active restriction polygon at restricted altitude fails."""
    sim = DigitalTwinSimulator(load_world())
    sim.advance(18)

    candidate = {
        "candidate_id": "ALT-FAIL-RESTRICTION",
        "flight_id": "F102",
        "route": ["W0", "W4", "W5", "W10", "W11", "W12", "BOM"],
        "speed_kt": 430,
        "cruise_altitude_ft": 34000,
    }

    res1 = validate_candidate(sim.state, candidate)
    assert res1["feasible"] is False
    assert any("airspace restriction" in r.lower() for r in res1["rejection_reasons"])

    res2 = validate_candidate(sim.state, candidate)
    assert res1 == res2


def test_failure_mode_4_sector_overload():
    """Failure Mode 4: Candidate traversing an overloaded sector fails capacity constraint."""
    state = load_world()
    state.sectors["S4"].capacity = 1
    state.sectors["S4"].current_traffic = 1

    candidate = {
        "candidate_id": "ALT-FAIL-SECTOR",
        "flight_id": "F102",
        "route": ["W0", "W4", "W5", "W7", "BOM"],
        "speed_kt": 430,
        "cruise_altitude_ft": 32000,
    }

    res1 = validate_candidate(state, candidate)
    assert res1["feasible"] is False
    assert any("Sector S4 exceeds capacity" in r for r in res1["rejection_reasons"])

    res2 = validate_candidate(state, candidate)
    assert res1 == res2


def test_failure_mode_5_conflict():
    """Failure Mode 5: Candidate introducing a spatial-temporal conflict fails conflict constraint."""
    state = load_world()
    target_flight = state.aircraft["F102"]
    candidate_route = ["W0", "W4", "W5", "W7", "BOM"]

    other = state.aircraft["AI2-01"]
    other.route = list(candidate_route)
    other.route_index = 0
    other.edge_progress_min = 0.0
    other.status = "AIRBORNE"
    other.speed_kt = target_flight.speed_kt

    candidate = {
        "candidate_id": "ALT-FAIL-CONFLICT",
        "flight_id": "F102",
        "route": candidate_route,
        "speed_kt": target_flight.speed_kt,
        "cruise_altitude_ft": target_flight.altitude_ft,
    }

    res1 = validate_candidate(state, candidate)
    assert res1["feasible"] is False
    assert any("conflict" in r.lower() for r in res1["rejection_reasons"])

    res2 = validate_candidate(state, candidate)
    assert res1 == res2

