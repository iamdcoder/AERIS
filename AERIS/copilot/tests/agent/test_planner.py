from copilot.agent.planner import (
    InterventionPlanner,
    InterventionType,
)


def flagship_state():
    return {
        "scenario_id": "mumbai_weather_crisis",
        "simulation_time_min": 17,
        "urgency": "HIGH",
        "alerts": [
            {
                "type": "AIRPORT_CAPACITY_DEGRADATION",
                "severity": "HIGH",
            },
            {
                "type": "SECTOR_CONGESTION",
                "severity": "HIGH",
            },
            {
                "type": "WEATHER_EXPANSION",
                "severity": "HIGH",
            },
        ],
        "target_flight_id": "F102",
        "target_flight": {
            "id": "F102",
            "status": "DEGRADED",
            "fuel_remaining_min": 108,
            "reserve_required_min": 45,
        },
        "airports": [
            {
                "id": "BOM",
                "operational_status": "DEGRADED",
            }
        ],
        "sectors": [
            {
                "id": "S4",
                "status": "STRESSED",
                "projected_utilization": 0.92,
            },
            {
                "id": "S5",
                "status": "STRESSED",
                "projected_utilization": 0.90,
            },
        ],
        "weather_cells": [
            {
                "id": "WX-BOM-01",
                "severity": "SEVERE",
            }
        ],
        "network_summary": {
            "aircraft_in_holding": 4,
        },
    }


def test_flagship_prioritizes_network_reroute():
    planner = InterventionPlanner()

    plan = planner.plan(flagship_state())

    assert plan.primary_intervention == InterventionType.REROUTE
    assert plan.generate_candidates is True

    candidate_types = plan.candidate_types()

    assert InterventionType.REROUTE.value in candidate_types
    assert InterventionType.ALTITUDE_SPEED.value in candidate_types
    assert InterventionType.TIMING_HOLD.value in candidate_types
    assert InterventionType.ALTERNATE_DIVERSION.value in candidate_types

    assert plan.candidate_budget == 4


def test_flagship_records_operational_evidence_signals():
    planner = InterventionPlanner()

    plan = planner.plan(flagship_state())

    assert "WEATHER_PRESSURE" in plan.evidence_signals
    assert "AIRPORT_CAPACITY_DEGRADATION" in plan.evidence_signals
    assert "SECTOR_CONGESTION" in plan.evidence_signals
    assert "HOLDING_DEMAND" in plan.evidence_signals
    assert "TARGET_FLIGHT_DEGRADED" in plan.evidence_signals
    assert "HIGH_URGENCY" in plan.evidence_signals


def test_no_disruption_means_monitor_only():
    planner = InterventionPlanner()

    state = {
        "scenario_id": "normal",
        "target_flight": {
            "id": "F101",
            "status": "NORMAL",
            "fuel_remaining_min": 150,
            "reserve_required_min": 45,
        },
        "airports": [
            {
                "id": "BOM",
                "operational_status": "NORMAL",
            }
        ],
        "sectors": [
            {
                "id": "S1",
                "status": "NORMAL",
                "projected_utilization": 0.50,
            }
        ],
        "weather_cells": [],
        "alerts": [],
        "network_summary": {
            "aircraft_in_holding": 0,
        },
        "urgency": "LOW",
    }

    plan = planner.plan(state)

    assert plan.primary_intervention == InterventionType.MONITOR
    assert plan.generate_candidates is False
    assert plan.candidate_types() == []


def test_degraded_airport_prioritizes_alternate_and_timing():
    planner = InterventionPlanner()

    state = {
        "scenario_id": "airport_degradation",
        "target_flight": {
            "id": "F205",
            "status": "DEGRADED",
            "fuel_remaining_min": 100,
            "reserve_required_min": 45,
        },
        "airports": [
            {
                "id": "BOM",
                "operational_status": "DEGRADED",
            }
        ],
        "sectors": [],
        "weather_cells": [],
        "alerts": [
            {
                "type": "AIRPORT_CAPACITY_DEGRADATION",
                "severity": "HIGH",
            }
        ],
        "network_summary": {
            "aircraft_in_holding": 6,
        },
        "urgency": "HIGH",
    }

    plan = planner.plan(state)

    assert plan.primary_intervention in {
        InterventionType.ALTERNATE_DIVERSION,
        InterventionType.TIMING_HOLD,
    }

    assert InterventionType.ALTERNATE_DIVERSION.value in plan.candidate_types()
    assert InterventionType.TIMING_HOLD.value in plan.candidate_types()


def test_low_fuel_buffer_increases_alternate_priority():
    planner = InterventionPlanner()

    state = {
        "scenario_id": "fuel_pressure",
        "target_flight": {
            "id": "F310",
            "status": "DEGRADED",
            "fuel_remaining_min": 105,
            "reserve_required_min": 45,
        },
        "airports": [
            {
                "id": "BOM",
                "operational_status": "DEGRADED",
            }
        ],
        "sectors": [],
        "weather_cells": [],
        "alerts": [],
        "network_summary": {
            "aircraft_in_holding": 1,
        },
        "urgency": "HIGH",
    }

    plan = planner.plan(state)

    alternate = next(
        intent
        for intent in plan.intervention_intents
        if intent.intervention_type == InterventionType.ALTERNATE_DIVERSION
    )

    timing = next(
        intent
        for intent in plan.intervention_intents
        if intent.intervention_type == InterventionType.TIMING_HOLD
    )

    assert alternate.priority > timing.priority


def test_planner_is_deterministic():
    planner = InterventionPlanner()

    first = planner.plan(flagship_state())
    second = planner.plan(flagship_state())

    assert first.model_dump() == second.model_dump()


def test_tool_request_contains_only_selected_interventions():
    planner = InterventionPlanner()

    plan = planner.plan(flagship_state())
    request = plan.to_tool_request()

    assert request["tool_name"] == "generate_alternatives"

    args = request["arguments"]

    assert args["flight_id"] == "F102"
    assert args["max_candidates"] == 4

    assert set(args["intervention_types"]) == {
        "REROUTE",
        "ALTITUDE_SPEED",
        "TIMING_HOLD",
        "ALTERNATE_DIVERSION",
    }


def test_agent_context_is_compact_and_structured():
    planner = InterventionPlanner()

    plan = planner.plan(flagship_state())
    context = plan.to_agent_context()

    assert context["scenario_id"] == "mumbai_weather_crisis"
    assert context["target_flight_id"] == "F102"
    assert context["primary_intervention"] == "REROUTE"
    assert context["fallback_intervention"] == "MONITOR"

    assert isinstance(
        context["candidate_intervention_types"],
        list,
    )

    assert isinstance(
        context["required_tools"],
        list,
    )