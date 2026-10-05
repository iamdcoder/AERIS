from dataclasses import dataclass, field
from typing import Any

from copilot.tools.base import ToolResult
from copilot.tools.registry import ToolRegistry


@dataclass(frozen=True)
class ToolPolicy:
    """
    Defines which tools the agent is allowed to see and invoke
    during a particular stage of the AERIS workflow.

    This is a safety/control layer, not an LLM prompt.
    """

    stage: str

    allowed_tools: frozenset[str]

    max_total_calls: int = 12

    max_calls_per_tool: int = 3

    # These tools are never exposed to the LLM directly.
    # Consequential actions must remain application-controlled.
    permanently_blocked_tools: frozenset[str] = frozenset(
        {
            "apply_intervention",
            "execute_intervention",
            "approve_intervention",
            "reject_intervention",
        }
    )

    @classmethod
    def investigation(cls) -> "ToolPolicy":
        return cls(
            stage="INVESTIGATION",
            allowed_tools=frozenset(
                {
                    "get_airspace_state",
                    "get_disruptions",
                    "get_target_flight",
                    "get_sector_state",
                    "get_airport_state",
                    "get_weather_state",
                    "get_restrictions",
                    "get_network_metrics",
                }
            ),
            max_total_calls=12,
            max_calls_per_tool=3,
        )

    @classmethod
    def planning(cls) -> "ToolPolicy":
        return cls(
            stage="PLANNING",
            allowed_tools=frozenset(
                {
                    "get_airspace_state",
                    "get_disruptions",
                    "get_target_flight",
                    "get_sector_state",
                    "get_airport_state",
                    "get_weather_state",
                    "get_restrictions",
                    "get_network_metrics",
                    "generate_alternatives",
                    "validate_candidate",
                }
            ),
            max_total_calls=20,
            max_calls_per_tool=5,
        )

    @classmethod
    def evaluation(cls) -> "ToolPolicy":
        return cls(
            stage="EVALUATION",
            allowed_tools=frozenset(
                {
                    "get_airspace_state",
                    "get_target_flight",
                    "get_sector_state",
                    "get_airport_state",
                    "get_network_metrics",
                    "validate_candidate",
                    "simulate_network_impact",
                }
            ),
            max_total_calls=25,
            max_calls_per_tool=8,
        )

    @classmethod
    def stress_testing(cls) -> "ToolPolicy":
        return cls(
            stage="STRESS_TEST",
            allowed_tools=frozenset(
                {
                    "get_airspace_state",
                    "get_sector_state",
                    "get_network_metrics",
                    "simulate_network_impact",
                    "stress_test_candidate",
                }
            ),
            max_total_calls=30,
            max_calls_per_tool=10,
        )

    @classmethod
    def critic(cls) -> "ToolPolicy":
        return cls(
            stage="CRITIC",
            allowed_tools=frozenset(
                {
                    "get_airspace_state",
                    "get_sector_state",
                    "get_airport_state",
                    "get_network_metrics",
                    "simulate_network_impact",
                    "stress_test_candidate",
                }
            ),
            max_total_calls=20,
            max_calls_per_tool=8,
        )

    def allows(
        self,
        tool_name: str,
    ) -> bool:
        if (
            tool_name
            in self.permanently_blocked_tools
        ):
            return False

        return (
            tool_name
            in self.allowed_tools
        )


class GuardedToolRegistry:
    """
    Security/policy wrapper around the normal ToolRegistry.

    The wrapped registry remains responsible for actual tool
    execution. This layer decides whether the model is allowed
    to request that tool in the current stage.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        policy: ToolPolicy,
    ) -> None:
        self.registry = registry

        self.policy = policy

        self.total_calls = 0

        self.calls_by_tool: dict[
            str,
            int,
        ] = {}

    def reset(self) -> None:
        self.total_calls = 0
        self.calls_by_tool = {}

    def list_tools(self):
        return [
            tool
            for tool in self.registry.list_tools()
            if self.policy.allows(
                tool.name
            )
        ]

    def definitions(self) -> list[dict[str, Any]]:
        return [
            tool.definition()
            for tool
            in self.list_tools()
        ]

    def function_declarations(
        self,
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": definition["name"],
                "description": definition[
                    "description"
                ],
                "parameters": definition[
                    "parameters"
                ],
            }
            for definition
            in self.definitions()
        ]

    def _validate_arguments(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult | None:
        tool = self.registry.get(
            tool_name
        )

        schema = tool.parameters

        properties = schema.get(
            "properties",
            {},
        )

        required = schema.get(
            "required",
            [],
        )

        missing = [
            name
            for name
            in required
            if name not in arguments
        ]

        if missing:
            return ToolResult.failure(
                tool_name=tool_name,
                error_code="MISSING_REQUIRED_ARGUMENT",
                error_message=(
                    "Missing required argument(s): "
                    + ", ".join(missing)
                ),
                summary=(
                    "The requested tool call is missing "
                    "required parameters."
                ),
            )

        unexpected = [
            name
            for name
            in arguments
            if name not in properties
        ]

        if unexpected:
            return ToolResult.failure(
                tool_name=tool_name,
                error_code="UNEXPECTED_ARGUMENT",
                error_message=(
                    "Unexpected argument(s): "
                    + ", ".join(unexpected)
                ),
                summary=(
                    "The requested tool call contains "
                    "unsupported parameters."
                ),
            )

        return None

    def invoke(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolResult:
        arguments = arguments or {}

        if not self.policy.allows(
            tool_name
        ):
            return ToolResult.failure(
                tool_name=tool_name,
                error_code="TOOL_NOT_ALLOWED",
                error_message=(
                    f"Tool '{tool_name}' is not allowed "
                    f"during stage {self.policy.stage}."
                ),
                summary=(
                    f"Tool blocked by AERIS policy "
                    f"for stage {self.policy.stage}."
                ),
            )

        if (
            self.total_calls
            >= self.policy.max_total_calls
        ):
            return ToolResult.failure(
                tool_name=tool_name,
                error_code="TOOL_CALL_BUDGET_EXCEEDED",
                error_message=(
                    f"Stage {self.policy.stage} exceeded "
                    "its total tool-call budget."
                ),
                summary=(
                    "Tool call blocked because the stage "
                    "tool budget has been exhausted."
                ),
            )

        tool_call_count = (
            self.calls_by_tool.get(
                tool_name,
                0,
            )
        )

        if (
            tool_call_count
            >= self.policy.max_calls_per_tool
        ):
            return ToolResult.failure(
                tool_name=tool_name,
                error_code="TOOL_REPETITION_LIMIT",
                error_message=(
                    f"Tool '{tool_name}' exceeded its "
                    "per-tool invocation limit."
                ),
                summary=(
                    "Tool call blocked because the "
                    "per-tool repetition limit was reached."
                ),
            )

        argument_error = (
            self._validate_arguments(
                tool_name,
                arguments,
            )
        )

        if argument_error is not None:
            return argument_error

        self.total_calls += 1

        self.calls_by_tool[
            tool_name
        ] = (
            tool_call_count + 1
        )

        return self.registry.invoke(
            tool_name,
            arguments,
        )