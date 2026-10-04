from copilot.mock_engine import (
    MockEngineClient,
)

from copilot.tools import (
    ToolRegistry,
    build_default_registry,
)


def test_mock_engine_loads_deterministic_state():
    engine = (
        MockEngineClient()
    )

    first = engine.get_state()
    second = engine.get_state()

    assert first == second

    assert (
        first["mode"]
        == "DETERMINISTIC_MOCK"
    )

    assert (
        first["target_flight_id"]
        == "F102"
    )


def test_mock_engine_returns_five_candidates():
    engine = (
        MockEngineClient()
    )

    candidates = (
        engine.get_alternatives(
            "F102"
        )
    )

    assert len(candidates) == 5

    assert {
        item["candidate_id"]
        for item in candidates
    } == {
        "ALT-A",
        "ALT-B",
        "ALT-C",
        "ALT-D",
        "ALT-E",
    }


def test_mock_engine_does_not_expose_mutable_internal_state():
    engine = (
        MockEngineClient()
    )

    state = engine.get_state()

    state[
        "network_summary"
    ][
        "active_aircraft"
    ] = 999

    fresh = engine.get_state()

    assert (
        fresh[
            "network_summary"
        ][
            "active_aircraft"
        ]
        == 48
    )


def test_weather_tool_returns_weather_cells():
    registry = (
        build_default_registry()
    )

    result = registry.invoke(
        "get_weather_state"
    )

    assert result.ok is True

    assert result.data[
        "weather_cells"
    ]

    assert (
        result.data[
            "weather_cells"
        ][0]["severity"]
        == "SEVERE"
    )


def test_restriction_tool_returns_structured_state():
    registry = (
        build_default_registry()
    )

    result = registry.invoke(
        "get_restrictions"
    )

    assert result.ok is True

    assert (
        "restrictions"
        in result.data
    )

    assert isinstance(
        result.data[
            "restrictions"
        ],
        list,
    )


def test_default_registry_contains_expected_tools():
    registry = (
        build_default_registry()
    )

    tool_names = {
        tool.name
        for tool
        in registry.list_tools()
    }

    assert tool_names == {
        "get_airspace_state",
        "get_disruptions",
        "get_target_flight",
        "get_sector_state",
        "get_airport_state",
        "get_weather_state",
        "get_restrictions",
        "generate_alternatives",
        "validate_candidate",
        "simulate_network_impact",
        "get_network_metrics",
        "stress_test_candidate",
    }


def test_tool_definitions_are_structured():
    registry = (
        build_default_registry()
    )

    definitions = (
        registry.definitions()
    )

    assert len(definitions) == 12

    for definition in definitions:
        assert "name" in definition

        assert (
            "description"
            in definition
        )

        assert (
            "parameters"
            in definition
        )

        assert (
            definition[
                "parameters"
            ][
                "type"
            ]
            == "object"
        )


def test_airspace_tool_returns_structured_result():
    registry = (
        build_default_registry()
    )

    result = registry.invoke(
        "get_airspace_state"
    )

    assert result.ok is True

    assert (
        result.tool_name
        == "get_airspace_state"
    )

    assert (
        result.data[
            "target_flight_id"
        ]
        == "F102"
    )

    assert result.evidence


def test_validation_tool_returns_constraint_result():
    registry = (
        build_default_registry()
    )

    result = registry.invoke(
        "validate_candidate",
        {
            "candidate_id": "ALT-E"
        },
    )

    assert result.ok is True

    assert (
        result.data["feasible"]
        is False
    )

    assert result.data[
        "rejection_reasons"
    ]


def test_unknown_tool_does_not_crash_registry():
    registry = ToolRegistry()

    result = registry.invoke(
        "does_not_exist"
    )

    assert result.ok is False

    assert (
        result.error_code
        == "TOOL_NOT_FOUND"
    )