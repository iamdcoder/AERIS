from copilot.agent.guardrails import (
    GuardedToolRegistry,
    ToolPolicy,
)
from copilot.tools import (
    build_default_registry,
)


def test_investigation_policy_exposes_only_read_tools():
    registry = (
        build_default_registry()
    )

    guarded = GuardedToolRegistry(
        registry,
        ToolPolicy.investigation(),
    )

    names = {
        tool.name
        for tool
        in guarded.list_tools()
    }

    assert names == {
        "get_airspace_state",
        "get_disruptions",
        "get_target_flight",
        "get_sector_state",
        "get_airport_state",
        "get_weather_state",
        "get_restrictions",
        "get_network_metrics",
    }


def test_investigation_policy_blocks_candidate_generation():
    registry = (
        build_default_registry()
    )

    guarded = GuardedToolRegistry(
        registry,
        ToolPolicy.investigation(),
    )

    result = guarded.invoke(
        "generate_alternatives",
        {
            "flight_id": "F102"
        },
    )

    assert result.ok is False

    assert (
        result.error_code
        == "TOOL_NOT_ALLOWED"
    )


def test_investigation_policy_blocks_execution_tools_even_if_added():
    registry = (
        build_default_registry()
    )

    policy = ToolPolicy(
        stage="TEST",
        allowed_tools=frozenset(
            {
                "apply_intervention"
            }
        ),
    )

    guarded = GuardedToolRegistry(
        registry,
        policy,
    )

    result = guarded.invoke(
        "apply_intervention",
        {
            "candidate_id": "ALT-D"
        },
    )

    assert result.ok is False

    assert (
        result.error_code
        == "TOOL_NOT_ALLOWED"
    )


def test_missing_required_argument_is_blocked_before_execution():
    registry = (
        build_default_registry()
    )

    guarded = GuardedToolRegistry(
        registry,
        ToolPolicy.investigation(),
    )

    result = guarded.invoke(
        "get_target_flight"
    )

    assert result.ok is False

    assert (
        result.error_code
        == "MISSING_REQUIRED_ARGUMENT"
    )


def test_unexpected_argument_is_rejected():
    registry = (
        build_default_registry()
    )

    guarded = GuardedToolRegistry(
        registry,
        ToolPolicy.investigation(),
    )

    result = guarded.invoke(
        "get_target_flight",
        {
            "flight_id": "F102",
            "secret_internal_flag": True,
        },
    )

    assert result.ok is False

    assert (
        result.error_code
        == "UNEXPECTED_ARGUMENT"
    )


def test_total_tool_budget_is_enforced():
    registry = (
        build_default_registry()
    )

    policy = ToolPolicy(
        stage="TEST",
        allowed_tools=frozenset(
            {
                "get_airspace_state"
            }
        ),
        max_total_calls=2,
        max_calls_per_tool=10,
    )

    guarded = GuardedToolRegistry(
        registry,
        policy,
    )

    first = guarded.invoke(
        "get_airspace_state"
    )

    second = guarded.invoke(
        "get_airspace_state"
    )

    third = guarded.invoke(
        "get_airspace_state"
    )

    assert first.ok is True
    assert second.ok is True
    assert third.ok is False

    assert (
        third.error_code
        == "TOOL_CALL_BUDGET_EXCEEDED"
    )


def test_per_tool_repetition_limit_is_enforced():
    registry = (
        build_default_registry()
    )

    policy = ToolPolicy(
        stage="TEST",
        allowed_tools=frozenset(
            {
                "get_airspace_state"
            }
        ),
        max_total_calls=10,
        max_calls_per_tool=2,
    )

    guarded = GuardedToolRegistry(
        registry,
        policy,
    )

    first = guarded.invoke(
        "get_airspace_state"
    )

    second = guarded.invoke(
        "get_airspace_state"
    )

    third = guarded.invoke(
        "get_airspace_state"
    )

    assert first.ok is True
    assert second.ok is True
    assert third.ok is False

    assert (
        third.error_code
        == "TOOL_REPETITION_LIMIT"
    )


def test_policy_resets_call_budget():
    registry = (
        build_default_registry()
    )

    policy = ToolPolicy(
        stage="TEST",
        allowed_tools=frozenset(
            {
                "get_airspace_state"
            }
        ),
        max_total_calls=1,
        max_calls_per_tool=1,
    )

    guarded = GuardedToolRegistry(
        registry,
        policy,
    )

    first = guarded.invoke(
        "get_airspace_state"
    )

    assert first.ok is True

    blocked = guarded.invoke(
        "get_airspace_state"
    )

    assert blocked.ok is False

    guarded.reset()

    after_reset = guarded.invoke(
        "get_airspace_state"
    )

    assert after_reset.ok is True