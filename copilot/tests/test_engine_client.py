import ast
import inspect

import pytest

from copilot.agent.orchestrator import (
    AgentOrchestrator,
)
from copilot.engine.client import (
    RealEngineClient,
)
from copilot.mock_engine import (
    MockEngineClient,
)
from copilot.tools import (
    build_default_registry,
)


def test_real_adapter_smoke_and_candidate_lifecycle():
    engine = RealEngineClient()
    engine.reset_engine()

    state = engine.get_airspace_state()
    target = engine.get_target_flight(
        "F102"
    )
    candidates = engine.get_alternatives(
        "F102"
    )

    assert state["time_min"] == 0

    assert (
        target is not None
        and target["id"] == "F102"
    )

    assert [
        item["candidate_id"]
        for item in candidates
    ] == [
        "ALT-A",
        "ALT-B",
        "ALT-C",
        "ALT-D",
        "ALT-E",
    ]

    repeated = engine.get_alternatives(
        "F102"
    )

    assert candidates == repeated

    candidate_id = candidates[0][
        "candidate_id"
    ]

    assert (
        engine.get_candidate(
            candidate_id
        )
        == candidates[0]
    )

    assert (
        engine.validate_candidate(
            candidate_id
        )["candidate_id"]
        == candidate_id
    )

    assert (
        engine.get_simulation_result(
            candidate_id
        )["candidate_id"]
        == candidate_id
    )

    stress = engine.get_stress_result(
        candidate_id
    )

    assert (
        stress is not None
        and "passed" in stress
        and "total" in stress
    )

    scored = engine.score_candidates(
        [candidate_id]
    )

    assert len(scored) == 1

    assert (
        scored[0]["candidate_id"]
        == candidate_id
    )

    assert (
        "decision_score"
        in scored[0]
    )


def test_real_adapter_projects_current_disruption_capabilities():
    """
    get_disruptions() is a Copilot-facing operational view.

    It intentionally projects current disruption signals from the
    deterministic airspace snapshot instead of exposing the engine's
    internal event log directly.
    """

    engine = RealEngineClient()
    engine.reset_engine()

    state = (
        engine.get_airspace_state()
    )

    disruptions = (
        engine.get_disruptions()
    )

    assert isinstance(
        disruptions,
        list,
    )

    assert all(
        isinstance(
            item,
            dict,
        )
        for item in disruptions
    )

    assert all(
        "type" in item
        and "severity" in item
        and "summary" in item
        for item in disruptions
    )

    weather_cells = state.get(
        "weather_cells",
        [],
    )

    if weather_cells:
        assert any(
            item["type"]
            == "WEATHER_EXPANSION"
            for item in disruptions
        )

    sectors = state.get(
        "sectors",
        [],
    )

    stressed_sectors = []

    for sector in sectors:
        if not isinstance(
            sector,
            dict,
        ):
            continue

        status = str(
            sector.get(
                "status",
                "",
            )
        ).upper()

        utilization = sector.get(
            "utilization_pct"
        )

        if utilization is None:
            utilization = sector.get(
                "projected_utilization"
            )

        try:
            utilization_value = float(
                utilization
            )
        except (
            TypeError,
            ValueError,
        ):
            utilization_value = 0.0

        if utilization_value <= 2:
            utilization_value *= 100

        if (
            status
            in {
                "STRESSED",
                "CONGESTED",
                "OVERLOADED",
                "CRITICAL",
            }
            or utilization_value >= 85
        ):
            stressed_sectors.append(
                sector.get("id")
            )

    if stressed_sectors:
        assert any(
            item["type"]
            == "SECTOR_CONGESTION"
            for item in disruptions
        )

    assert (
        engine.get_sector_state(
            state["sectors"][0]["id"]
        )
        is not None
    )

    assert (
        engine.get_airport_state(
            state["airports"][0]["id"]
        )
        is not None
    )

    weather = (
        engine.get_weather_state()
    )

    assert isinstance(
        weather,
        list,
    )

    if weather_cells:
        assert (
            weather[0]["severity"]
            == weather_cells[0][
                "intensity"
            ]
        )

    assert isinstance(
        engine.get_restrictions(),
        list,
    )

    assert (
        "sector_utilization_pct"
        in engine.get_network_metrics()
    )


def test_real_registry_preserves_candidate_identity_across_tools():
    engine = RealEngineClient()
    engine.reset_engine()

    registry = (
        build_default_registry(
            engine
        )
    )

    generated = registry.invoke(
        "generate_alternatives",
        {
            "flight_id": "F102"
        },
    )

    candidates = generated.data[
        "alternatives"
    ]

    candidate = next(
        item
        for item in candidates
        if item["candidate_id"]
        == "ALT-D"
    )

    candidate_id = (
        candidate["candidate_id"]
    )

    validation = registry.invoke(
        "validate_candidate",
        {
            "candidate_id":
                candidate_id
        },
    )

    simulation = registry.invoke(
        "simulate_network_impact",
        {
            "candidate_id":
                candidate_id
        },
    )

    stress = registry.invoke(
        "stress_test_candidate",
        {
            "candidate_id":
                candidate_id
        },
    )

    assert (
        generated.ok
        and validation.ok
        and simulation.ok
        and stress.ok
    )

    assert (
        validation.data[
            "candidate_id"
        ]
        == candidate_id
    )

    assert (
        simulation.data[
            "candidate_id"
        ]
        == candidate_id
    )

    assert (
        stress.data[
            "candidate_id"
        ]
        == candidate_id
    )

    assert (
        engine.get_candidate(
            candidate_id
        )["route"]
        == candidate["route"]
    )


def test_real_adapter_shared_state_advance_and_reset():
    engine = RealEngineClient()
    engine.reset_engine()

    registry = (
        build_default_registry(
            engine
        )
    )

    initial = (
        registry
        .invoke(
            "get_airspace_state"
        )
        .data
    )

    advanced = (
        engine.advance_simulation(
            2
        )
    )

    assert (
        advanced["time_min"]
        == initial["time_min"]
        + 2
    )

    assert (
        registry
        .invoke(
            "get_airspace_state"
        )
        .data["time_min"]
        == advanced["time_min"]
    )

    engine.reset_engine()

    assert (
        registry
        .invoke(
            "get_airspace_state"
        )
        .data["time_min"]
        == initial["time_min"]
    )


def test_real_adapter_applies_and_verifies_feasible_candidate():
    engine = RealEngineClient()
    engine.reset_engine()

    candidates = (
        engine.get_alternatives(
            "F102"
        )
    )

    feasible = next(
        candidate
        for candidate
        in candidates
        if engine.validate_candidate(
            candidate[
                "candidate_id"
            ]
        )["feasible"]
    )

    applied = (
        engine.apply_intervention(
            feasible[
                "candidate_id"
            ]
        )
    )

    verification = (
        engine.verify_state(
            feasible[
                "candidate_id"
            ]
        )
    )

    assert applied == {
        "status": "EXECUTING",
        "candidate_id":
            feasible[
                "candidate_id"
            ],
        "flight_id": "F102",
    }

    assert (
        verification["status"]
        in {
            "VERIFIED",
            "REASSESSMENT_REQUIRED",
        }
    )

    assert (
        verification[
            "reassessment_required"
        ]
        is (
            verification["status"]
            == "REASSESSMENT_REQUIRED"
        )
    )


def test_invalid_candidate_cannot_be_applied():
    engine = RealEngineClient()
    engine.reset_engine()

    engine.advance_simulation(
        19
    )

    candidates = (
        engine.get_alternatives(
            "F102"
        )
    )

    invalid = next(
        candidate
        for candidate
        in candidates
        if engine.validate_candidate(
            candidate[
                "candidate_id"
            ]
        )["feasible"]
        is False
    )

    with pytest.raises(
        ValueError,
        match="infeasible",
    ):
        engine.apply_intervention(
            invalid[
                "candidate_id"
            ]
        )


def test_mock_remains_injectable_for_unit_tests():
    registry = (
        build_default_registry(
            MockEngineClient()
        )
    )

    result = registry.invoke(
        "get_weather_state"
    )

    assert result.ok
    assert result.data[
        "weather_cells"
    ]


def test_default_orchestrator_does_not_construct_mock_engine():
    orchestrator = (
        AgentOrchestrator()
    )

    assert isinstance(
        orchestrator.engine,
        RealEngineClient,
    )

    assert all(
        not isinstance(
            tool.engine,
            MockEngineClient,
        )
        for tool
        in orchestrator.registry.list_tools()
    )


def test_only_engine_adapter_imports_public_facade():
    from copilot.engine import client

    tree = ast.parse(
        inspect.getsource(
            client
        )
    )

    imports = [
        node.module or ""
        for node
        in ast.walk(tree)
        if isinstance(
            node,
            ast.ImportFrom,
        )
    ]

    assert (
        "backend.app.engine"
        in imports
    )