from typing import Any

from copilot.llm import (
    GeminiClient,
    GeminiRunResult,
)
from copilot.tools import (
    ToolRegistry,
    build_default_registry,
)

from .prompts import (
    AERIS_AGENT_SYSTEM_PROMPT,
    build_investigation_prompt,
)


class GeminiInvestigator:
    """
    AERIS investigation runner backed by Gemini.

    It is deliberately separate from the deterministic
    AgentOrchestrator during this phase.

    This lets us:
    - test Gemini independently;
    - preserve the deterministic fallback;
    - compare LLM behavior against fixed expectations;
    - integrate the LLM gradually rather than rewriting the agent.
    """

    def __init__(
        self,
        *,
        registry: ToolRegistry | None = None,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self.registry = (
            registry
            or build_default_registry()
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
    ) -> GeminiRunResult:
        prompt = (
            build_investigation_prompt(
                target_flight_id=(
                    target_flight_id
                ),
                scenario_id=scenario_id,
            )
        )

        return self.gemini.run(
            prompt=prompt,
            registry=self.registry,
            system_instruction=(
                AERIS_AGENT_SYSTEM_PROMPT
            ),
        )

    def tool_definitions(
        self,
    ) -> list[dict[str, Any]]:
        return (
            self.registry
            .function_declarations()
        )