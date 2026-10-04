import pytest
from shapely.geometry import Polygon

from app.engine.digital_twin.loaders import load_world
from app.engine.digital_twin.simulator import DigitalTwinSimulator


def test_flagship_has_40_aircraft():
    sim = DigitalTwinSimulator(load_world())
    assert len(sim.state.aircraft) == 40
    assert "F102" in sim.state.aircraft
    assert sim.state.time_min == 0
    assert "BOM" in sim.state.airports
    assert "S6" in sim.state.sectors
    assert "WX-BOM-01" in sim.state.weather_cells
    assert "R-MONSOON-01" in sim.state.restrictions


def test_simulation_advances_one_minute():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(1)
    assert sim.state.time_min == 1


def test_weather_event_at_t5():
    sim = DigitalTwinSimulator(load_world())
    initial_weather = sim.state.weather_cells["WX-BOM-01"]
    initial_intensity = initial_weather.intensity

    sim.advance(4)
    assert sim.state.time_min == 4
    assert sim.state.weather_cells["WX-BOM-01"].intensity == initial_intensity
    geom_t4 = Polygon(sim.state.weather_cells["WX-BOM-01"].geometry["coordinates"][0])

    sim.advance(1)
    assert sim.state.time_min == 5
    cell = sim.state.weather_cells["WX-BOM-01"]
    assert cell.intensity == "HIGH"
    assert cell.uncertainty == 0.25
    geom_t5 = Polygon(cell.geometry["coordinates"][0])
    assert geom_t5.area > geom_t4.area


def test_bom_arrival_capacity_drops_at_t8():
    sim = DigitalTwinSimulator(load_world())
    assert sim.state.airports["BOM"].arrival_capacity == 18

    sim.advance(7)
    assert sim.state.airports["BOM"].arrival_capacity == 18

    sim.advance(1)
    assert sim.state.time_min == 8
    assert sim.state.airports["BOM"].arrival_capacity == 12
    assert sim.state.airports["BOM"].weather_status == "SEVERE_CONVECTIVE"


def test_holding_begins_at_t10():
    sim = DigitalTwinSimulator(load_world())
    expected_holding = {"AI2-01", "AI3-01", "AI5-01", "AI8-01"}

    sim.advance(9)
    assert not expected_holding.intersection(sim.state.holding_flights)

    sim.advance(1)
    assert sim.state.time_min == 10
    assert expected_holding.issubset(sim.state.holding_flights)


def test_s6_capacity_changes_at_t12():
    sim = DigitalTwinSimulator(load_world())
    assert sim.state.sectors["S6"].capacity == 7

    sim.advance(11)
    assert sim.state.sectors["S6"].capacity == 7

    sim.advance(1)
    assert sim.state.time_min == 12
    assert sim.state.sectors["S6"].capacity == 6
    assert sim.state.sectors["S6"].forecast_traffic >= sim.state.sectors["S6"].capacity - 1


def test_f102_degrades_at_t15():
    sim = DigitalTwinSimulator(load_world())
    assert sim.state.aircraft["F102"].status != "DEGRADED"

    sim.advance(14)
    assert sim.state.aircraft["F102"].status != "DEGRADED"

    sim.advance(1)
    assert sim.state.time_min == 15
    assert sim.state.aircraft["F102"].status == "DEGRADED"
    # Event payload sets fuel to 51.0, but the t=15 tick consumption step reduces it by 1.0 burn rate to 50.0
    assert sim.state.aircraft["F102"].fuel_remaining_min == pytest.approx(50.0)


def test_f102_is_held_during_decision_window():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(15)

    flight = sim.state.aircraft["F102"]
    starting_route_index = flight.route_index
    starting_delay = flight.delay_min
    starting_fuel = flight.fuel_remaining_min

    sim.advance(5)
    assert flight.route_index == starting_route_index
    assert flight.delay_min == pytest.approx(starting_delay + 3.0)
    assert flight.fuel_remaining_min == pytest.approx(starting_fuel - 5.0)


def test_temporary_restriction_activates_at_t18():
    sim = DigitalTwinSimulator(load_world())
    assert sim.state.restrictions["R-MONSOON-01"].active is False

    sim.advance(17)
    assert sim.state.restrictions["R-MONSOON-01"].active is False

    sim.advance(1)
    assert sim.state.time_min == 18
    assert sim.state.restrictions["R-MONSOON-01"].active is True


def test_event_log_contains_applied_events():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(18)

    event_names = [event["event"] for event in sim.state.event_log]
    expected_events = [
        "convective_weather_develops_near_BOM",
        "BOM_arrival_capacity_drops",
        "holding_begins",
        "bypass_sector_approaches_capacity",
        "F102_operational_degradation",
        "generate_5_alternatives",
        "activate_temporary_restriction",
    ]
    for expected in expected_events:
        assert expected in event_names


def test_world_state_clone_is_independent():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(10)

    clone = sim.state.clone()
    clone.time_min += 100
    clone.aircraft["F102"].delay_min += 50.0

    assert sim.state.time_min != clone.time_min
    assert sim.state.aircraft["F102"].delay_min != clone.aircraft["F102"].delay_min


def test_snapshot_contains_core_world_sections():
    sim = DigitalTwinSimulator(load_world())
    snapshot = sim.state.snapshot()

    required_sections = {
        "time_min",
        "aircraft",
        "sectors",
        "airports",
        "weather_cells",
        "restrictions",
        "events",
    }
    assert required_sections.issubset(snapshot.keys())
    assert snapshot["time_min"] == 0
    assert len(snapshot["aircraft"]) == 40


def test_simulation_is_deterministic():
    checkpoints = [0, 5, 8, 10, 12, 15, 18, 21, 35]
    for cp in checkpoints:
        sim_a = DigitalTwinSimulator(load_world())
        sim_b = DigitalTwinSimulator(load_world())
        assert sim_a.advance(cp).snapshot() == sim_b.advance(cp).snapshot()




def test_flagship_reaches_end_of_scenario():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(35)

    assert sim.state.time_min == 35
    assert "F102" in sim.state.aircraft
    event_names = [event["event"] for event in sim.state.event_log]
    assert "continue_monitoring" in event_names


# ===========================================================================
# HOLDING STATE SEMANTICS (Part 1 / 2)
# ===========================================================================

def test_holding_aircraft_has_status_holding_after_t10():
    """Aircraft in the holding_begins payload should have status HOLDING after t=10."""
    sim = DigitalTwinSimulator(load_world())
    sim.advance(10)
    for fid in {"AI2-01", "AI3-01", "AI5-01", "AI8-01"}:
        assert sim.state.aircraft[fid].status == "HOLDING", (
            f"{fid} expected HOLDING, got {sim.state.aircraft[fid].status}"
        )


def test_holding_aircraft_route_index_does_not_advance():
    """HOLDING aircraft must not advance their route_index — they stay at the same waypoint."""
    sim = DigitalTwinSimulator(load_world())
    sim.advance(10)
    flight = sim.state.aircraft["AI2-01"]
    idx_at_10 = flight.route_index

    sim.advance(5)
    assert flight.route_index == idx_at_10, (
        f"route_index advanced during hold: {idx_at_10} -> {flight.route_index}"
    )


def test_holding_aircraft_accumulates_delay_at_1_min_per_min():
    """Each simulation minute in HOLDING adds exactly 1.0 min to delay_min."""
    import pytest

    sim = DigitalTwinSimulator(load_world())
    sim.advance(10)
    flight = sim.state.aircraft["AI2-01"]
    delay_at_10 = flight.delay_min

    sim.advance(3)
    assert flight.delay_min == pytest.approx(delay_at_10 + 3.0)


def test_holding_aircraft_burns_extra_fuel():
    """HOLDING aircraft consume base burn_rate + configured extra_fuel_burn_per_min per minute."""
    import pytest

    sim = DigitalTwinSimulator(load_world())
    sim.advance(10)
    flight = sim.state.aircraft["AI2-01"]
    fuel_at_10 = flight.fuel_remaining_min
    # Scenario configures extra_fuel_burn_per_min = 0.75
    expected_total_burn = (flight.burn_rate_min_per_min + 0.75) * 3

    sim.advance(3)
    assert flight.fuel_remaining_min == pytest.approx(fuel_at_10 - expected_total_burn)


def test_holding_ends_transitions_aircraft_back_to_airborne():
    """After holding_ends (scenario has no explicit end event, so manually trigger via state)."""
    sim = DigitalTwinSimulator(load_world())
    sim.advance(10)
    fid = "AI2-01"
    assert sim.state.aircraft[fid].status == "HOLDING"

    # Manually trigger holding_ends for this flight.
    sim._apply_event({"event": "holding_ends", "payload": {"affected_flights": [fid]}})
    assert sim.state.aircraft[fid].status == "AIRBORNE"
    assert fid not in sim.state.holding_flights


# ===========================================================================
# AIRCRAFT PERFORMANCE ENVELOPE (Part 3)
# ===========================================================================

def test_degraded_f102_rejected_at_high_altitude_candidate():
    """A degraded aircraft should fail a candidate with cruise altitude > 33,000 ft."""
    from app.engine.constraints.performance import performance_check

    sim = DigitalTwinSimulator(load_world())
    sim.advance(15)
    flight = sim.state.aircraft["F102"]
    assert flight.status == "DEGRADED"

    result = performance_check(sim.state, flight, cruise_altitude_ft=39000, speed_kt=430)
    assert result["passed"] is False
    assert "33000" in result["violation_reason"]


def test_degraded_f102_passes_at_low_altitude_candidate():
    """A degraded aircraft should pass a candidate at or below the degraded ceiling."""
    from app.engine.constraints.performance import performance_check

    sim = DigitalTwinSimulator(load_world())
    sim.advance(15)
    flight = sim.state.aircraft["F102"]
    assert flight.status == "DEGRADED"

    result = performance_check(sim.state, flight, cruise_altitude_ft=33000, speed_kt=430)
    assert result["passed"] is True


def test_normal_aircraft_passes_standard_altitude():
    """A healthy aircraft should pass a standard FL390 altitude candidate."""
    from app.engine.constraints.performance import performance_check

    state = load_world()
    flight = state.aircraft["F102"]
    # At t=0, F102 is AIRBORNE not DEGRADED.
    assert flight.status != "DEGRADED"

    result = performance_check(state, flight, cruise_altitude_ft=39000, speed_kt=430)
    assert result["passed"] is True
