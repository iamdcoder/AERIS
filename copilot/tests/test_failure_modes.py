import pytest

from copilot.agent.planner import (
    NoFeasibleCandidateError,
    select_initial_leader,
)
from copilot.llm import (
    GeminiConfigurationError,
)
from copilot.tools import (
    ToolRegistry,
    build_default_registry,
)


def test_no_feasible_candidates_fails_honestly():
    candidates = [
        {
            "candidate_id": "ALT-X",
            "feasible": False,
            "rejection_reasons": [
                "Fuel reserve below minimum"
            ],
        }
    ]

    with pytest.raises(
        NoFeasibleCandidateError,
        match="No safe candidate",
    ):
        select_initial_leader(
            candidates
        )


def test_missing_tool_argument_returns_structured_error():
    registry = (
        build_default_registry()
    )

    result = registry.invoke(
        "get_target_flight"
    )

    assert result.ok is False

    assert (
        result.error_code
        == "INVALID_ARGUMENTS"
    )


def test_bad_candidate_does_not_produce_successful_validation():
    registry = (
        build_default_registry()
    )

    result = registry.invoke(
        "validate_candidate",
        {
            "candidate_id": "UNKNOWN"
        },
    )

    assert result.ok is False

    assert (
        result.error_code
        == "CANDIDATE_NOT_FOUND"
    )


def test_malformed_tool_name_is_contained():
    registry = ToolRegistry()

    result = registry.invoke(
        "missing_tool",
        {},
    )

    assert result.ok is False

    assert (
        result.error_code
        == "TOOL_NOT_FOUND"
    )


def test_missing_weather_fixture_is_not_silently_invented():
    registry = (
        build_default_registry()
    )

    result = registry.invoke(
        "get_weather_state"
    )

    assert result.ok is True

    assert isinstance(
        result.data[
            "weather_cells"
        ],
        list,
    )


def test_tool_failure_is_structured():
    registry = (
        build_default_registry()
    )

    result = registry.invoke(
        "get_airport_state",
        {
            "airport_id": "UNKNOWN"
        },
    )

    assert result.ok is False

    assert (
        result.error_code
        == "AIRPORT_NOT_FOUND"
    )

    assert result.error_message


def test_gemini_requires_configuration_when_no_client_is_injected():
    with pytest.raises(
        GeminiConfigurationError
    ):
        from copilot.llm import GeminiClient

        GeminiClient(
            api_key=""
        )