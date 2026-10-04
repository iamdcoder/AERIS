import json
from copy import deepcopy

import networkx as nx
import pytest

from app.engine.digital_twin.loaders import load_world
from app.engine.digital_twin.simulator import DigitalTwinSimulator
from app.engine.digital_twin.state import WorldState
from app.engine.routes.generator import generate_candidate_routes
from app.engine.simulation import network as network_module
from app.engine.simulation.cascades import cascade_score
from app.engine.simulation.network import _advance_network, simulate_candidate
from app.models.aircraft import Aircraft, Position
from app.models.sector import Sector


def _controlled_state(*, capacity: int = 2, aircraft_count: int = 3) -> WorldState:
    graph = nx.DiGraph()
    coordinates = {
        "A": (0.0, 0.0),
        "B": (0.0, 10.0),
        "C": (0.0, 20.0),
        "D": (0.0, 0.0),
        "E": (0.0, 10.0),
        "F": (0.0, 20.0),
    }
    for node, (lat, lon) in coordinates.items():
        graph.add_node(node, lat=lat, lon=lon)
    graph.add_edges_from([("A", "B"), ("B", "C"), ("D", "E"), ("E", "F")])

    aircraft = {}
    for index in range(aircraft_count):
        flight_id = "T0" if index == 0 else f"B{index}"
        aircraft[flight_id] = Aircraft(
            id=flight_id,
            callsign=flight_id,
            position=Position(lat=0.0, lon=0.0),
            altitude_ft=30000,
            speed_kt=430,
            route=["A", "B", "C"],
            original_route=["A", "B", "C"],
            destination="C",
            fuel_remaining_min=300,
            status="AIRBORNE",
        )
    return WorldState(
        time_min=0,
        aircraft=aircraft,
        sectors={
            "S1": Sector(id="S1", geometry={}, nodes=["A"], capacity=capacity),
            "S2": Sector(id="S2", geometry={}, nodes=["D"], capacity=capacity),
        },
        airports={},
        weather_cells={},
        restrictions={},
        graph=graph,
        scenario={"events": []},
    )


def _candidate_for(flight_id: str = "T0") -> dict:
    return {
        "candidate_id": "TEST",
        "flight_id": flight_id,
        "intervention_type": "reroute",
        "strategy": "test_route",
        "route": ["D", "E", "F"],
        "cruise_altitude_ft": 30000,
        "speed_kt": 430,
        "timing_offset_min": 0,
        "hold_min": 0,
    }


def test_simulation_returns_required_fields_and_json_serializable():
    state = load_world()
    candidate = generate_candidate_routes(state.graph, "F102")[0]
    result = simulate_candidate(state, candidate, horizon_min=4)

    required = {
        "candidate_id",
        "target_delay_delta_min",
        "fuel_effect_min",
        "affected_flights",
        "network_delay_delta_min",
        "sector_utilization",
        "conflict_impact",
        "cascade_indicators",
        "baseline_total_delay_min",
        "candidate_total_delay_min",
    }
    assert required.issubset(result)
    assert isinstance(result["affected_flights"], int)
    json.dumps(result)


def test_simulation_is_deterministic_for_repeated_runs():
    state = load_world()
    candidate = generate_candidate_routes(state.graph, "F102")[0]
    assert simulate_candidate(state, candidate, horizon_min=5) == simulate_candidate(
        state, candidate, horizon_min=5
    )


def test_simulation_does_not_mutate_original_state():
    state = load_world()
    candidate = generate_candidate_routes(state.graph, "F102")[0]
    before_snapshot = state.snapshot()
    before_edges = deepcopy(list(state.graph.edges(data=True)))

    simulate_candidate(state, candidate, horizon_min=5)

    assert state.snapshot() == before_snapshot
    assert list(state.graph.edges(data=True)) == before_edges


def test_baseline_and_candidate_use_independent_cloned_states(monkeypatch):
    state = load_world()
    candidate = generate_candidate_routes(state.graph, "F102")[-1]
    original_advance = network_module._advance_network
    observed = []

    def capture(simulator, horizon_min):
        observed.append((simulator.state, simulator.state.graph, simulator.state.aircraft["F102"].route.copy()))
        return original_advance(simulator, horizon_min)

    monkeypatch.setattr(network_module, "_advance_network", capture)
    simulate_candidate(state, candidate, horizon_min=1)

    assert len(observed) == 2
    assert observed[0][0] is not observed[1][0]
    assert observed[0][1] is not observed[1][1]
    assert observed[0][0] is not state and observed[1][0] is not state
    assert observed[0][2] != observed[1][2]
    assert observed[0][0].aircraft.keys() == observed[1][0].aircraft.keys()
    for flight_id in observed[0][0].aircraft.keys() - {"F102"}:
        assert observed[0][0].aircraft[flight_id].model_dump() == observed[1][0].aircraft[flight_id].model_dump()


def test_sector_utilization_has_every_sector_and_numeric_values():
    state = load_world()
    candidate = generate_candidate_routes(state.graph, "F102")[0]
    result = simulate_candidate(state, candidate, horizon_min=3)

    assert set(result["sector_utilization"]) == set(state.sectors)
    assert all(isinstance(value, (int, float)) for value in result["sector_utilization"].values())


def test_delay_deltas_match_reported_world_totals():
    state = load_world()
    candidate = generate_candidate_routes(state.graph, "F102")[0]
    result = simulate_candidate(state, candidate, horizon_min=5)

    assert result["network_delay_delta_min"] == pytest.approx(
        result["candidate_total_delay_min"] - result["baseline_total_delay_min"], abs=0.011
    )
    assert result["target_delay_delta_min"] == pytest.approx(
        result["candidate_target_delay_min"] - result["baseline_target_delay_min"], abs=0.011
    )


def test_affected_flight_ids_are_sorted():
    result = simulate_candidate(_controlled_state(), _candidate_for(), horizon_min=2)
    ids = result["cascade_indicators"]["affected_flight_ids"]
    assert ids == sorted(ids)


def test_each_flight_gets_one_congestion_increment_per_sector_per_minute():
    state = _controlled_state(capacity=1, aircraft_count=3)
    simulator = DigitalTwinSimulator(state)
    summary = _advance_network(simulator, horizon_min=1)

    assert [state.aircraft[key].delay_min for key in sorted(state.aircraft)] == [1.5, 1.5, 1.5]
    assert summary["congestion_delay_by_sector"]["S1"] == 4.5


def test_increasing_overload_does_not_reduce_congestion_delay():
    light_state = _controlled_state(capacity=2, aircraft_count=3)
    heavy_state = _controlled_state(capacity=1, aircraft_count=3)
    light = _advance_network(DigitalTwinSimulator(light_state), horizon_min=1)
    heavy = _advance_network(DigitalTwinSimulator(heavy_state), horizon_min=1)

    assert heavy["congestion_delay_by_sector"]["S1"] >= light["congestion_delay_by_sector"]["S1"]


def test_cascade_score_is_numeric_and_deterministic():
    result = simulate_candidate(_controlled_state(), _candidate_for(), horizon_min=2)
    first = cascade_score(result)
    assert isinstance(first, float)
    assert first == cascade_score(result)
    assert cascade_score({"affected_flights": [], "cascade_indicators": None}) == 0.0


def test_candidate_relief_does_not_add_heuristic_ripple_delay():
    result = simulate_candidate(_controlled_state(capacity=2, aircraft_count=3), _candidate_for(), horizon_min=2)
    assert result["network_delay_delta_min"] <= 0.0
    assert result["candidate_total_delay_min"] <= result["baseline_total_delay_min"]
