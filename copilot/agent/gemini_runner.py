from typing import Any

from pydantic import BaseModel

from copilot.llm import (
    GeminiClient,
    GeminiRunResult,
)
from copilot.tools import (
    ToolRegistry,
    build_default_registry,
)

from .guardrails import (
    GuardedToolRegistry,
    ToolPolicy,
)
from .investigation_quality import (
    InvestigationQuality,
    assess_investigation_quality,
)
from .prompts import (
    AERIS_AGENT_SYSTEM_PROMPT,
    build_investigation_prompt,
)


class InvestigationRunResult(BaseModel):
    execution: GeminiRunResult

    quality: InvestigationQuality

    @property
    def status(self) -> str:
        if (
            self.execution.status
            != "COMPLETED"
        ):
            return self.execution.status

        if not self.quality.sufficient:
            return "INSUFFICIENT_EVIDENCE"

        return "COMPLETED"

    @property
    def final_text(self) -> str:
        return self.execution.final_text

    @property
    def tool_calls(self):
        return self.execution.tool_calls

    @property
    def rounds(self) -> int:
        return self.execution.rounds

    @property
    def errors(self) -> list[str]:
        return self.execution.errors


class GeminiInvestigator:
    """
    Gemini-backed AERIS investigation runner.

    Gemini can only see and invoke tools permitted by the
    INVESTIGATION ToolPolicy.
    """

    def __init__(
        self,
        *,
        registry: ToolRegistry | None = None,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self.base_registry = (
            registry
            or build_default_registry()
        )

        self.policy = (
            ToolPolicy.investigation()
        )

        self.registry = (
            GuardedToolRegistry(
                self.base_registry,
                self.policy,
            )
        )

        self.gemini = (
            gemini_client
            or GeminiClient()
        )

    def investigate(
        self,
        *,
        target_flight_id: str = "F102",
        scenario_id: str = (
            "mumbai_weather_crisis"
        ),
    ) -> InvestigationRunResult:
        self.registry.reset()

        prompt = (
            build_investigation_prompt(
                target_flight_id=(
                    target_flight_id
                ),
                scenario_id=scenario_id,
            )
        )

        execution = self.gemini.run(
            prompt=prompt,
            registry=self.registry,
            system_instruction=(
                AERIS_AGENT_SYSTEM_PROMPT
            ),
        )

        world_state_result = (
            self.base_registry.invoke(
                "get_airspace_state"
            )
        )

        world_state = (
            world_state_result.data
            if world_state_result.ok
            else {}
        )

        tool_names = [
            call.name
            for call
            in execution.tool_calls
            if call.ok
        ]

        quality = (
            assess_investigation_quality(
                tool_names=tool_names,
                world_state=world_state,
            )
        )

        if execution.status == "FAILED":
            quality.sufficient = False

            quality.reasons.append(
                (
                    "Gemini execution did not complete "
                    "successfully."
                )
            )

        return InvestigationRunResult(
            execution=execution,
            quality=quality,
        )

    def tool_definitions(
        self,
    ) -> list[dict[str, Any]]:
        return (
            self.registry
            .function_declarations()
        )

    def policy_snapshot(
        self,
    ) -> dict[str, Any]:
        return {
            "stage": self.policy.stage,
            "allowed_tools": sorted(
                self.policy.allowed_tools
            ),
            "max_total_calls": (
                self.policy.max_total_calls
            ),
            "max_calls_per_tool": (
                self.policy.max_calls_per_tool
            ),
            "permanently_blocked_tools": sorted(
                self.policy.permanently_blocked_tools
            ),
        }