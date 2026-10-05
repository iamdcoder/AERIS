from typing import Any

from pydantic import BaseModel, Field

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
from .memory import AgentMemory
from .prompts import (
    AERIS_AGENT_SYSTEM_PROMPT,
    build_investigation_prompt,
)
from .state import (
    InvestigationPlan,
    InvestigationPriority,
    InvestigationQuestion,
    InvestigationStatus,
)


class InvestigationRunResult(BaseModel):
    execution: GeminiRunResult

    quality: InvestigationQuality

    world_state: dict[str, Any] = Field(
        default_factory=dict
    )

    investigation_plan: InvestigationPlan | None = None

    investigation_results: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    evidence: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    working_memory: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

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

    Responsibilities:
    - expose investigation-safe tools;
    - execute the Gemini tool-calling loop;
    - capture structured tool results;
    - build investigation records;
    - build compact working memory;
    - assess whether sufficient evidence exists.
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
        initial_state: dict[str, Any] | None = None,
    ) -> InvestigationRunResult:
        self.registry.reset()

        world_state = (
            initial_state
            or self._load_initial_state()
        )

        prompt = (
            build_investigation_prompt(
                target_flight_id=(
                    target_flight_id
                ),
                scenario_id=scenario_id,
                initial_state=world_state,
            )
        )

        execution = self.gemini.run(
            prompt=prompt,
            registry=self.registry,
            system_instruction=(
                AERIS_AGENT_SYSTEM_PROMPT
            ),
        )

        successful_tool_names = [
            call.name
            for call
            in execution.tool_calls
            if call.ok
        ]

        quality = (
            assess_investigation_quality(
                tool_names=(
                    successful_tool_names
                ),
                world_state=world_state,
            )
        )

        if (
            execution.status
            == "FAILED"
        ):
            quality.sufficient = False

            quality.reasons.append(
                (
                    "Gemini investigation failed "
                    "before sufficient evidence was collected."
                )
            )

        evidence = []

        memory = AgentMemory()

        investigation_results = []

        questions = []

        for index, call in enumerate(
            execution.tool_calls,
            start=1,
        ):
            status = (
                InvestigationStatus.COMPLETED
                if call.ok
                else InvestigationStatus.FAILED
            )

            priority = (
                InvestigationPriority.HIGH
                if call.name
                in {
                    "get_target_flight",
                    "get_weather_state",
                    "get_sector_state",
                }
                else InvestigationPriority.MEDIUM
            )

            question = (
                InvestigationQuestion(
                    question_id=(
                        f"GEM-{index:02d}"
                    ),
                    question=(
                        f"Investigate capability "
                        f"{call.name}."
                    ),
                    rationale=(
                        "Requested dynamically by "
                        "the Gemini investigation."
                    ),
                    tool_name=call.name,
                    arguments=(
                        call.arguments
                    ),
                    priority=priority,
                    status=status,
                    result_summary=(
                        call.result_summary
                    ),
                )
            )

            questions.append(
                question
            )

            investigation_results.append(
                {
                    "question_id": (
                        question.question_id
                    ),
                    "tool_name": call.name,
                    "arguments": (
                        call.arguments
                    ),
                    "status": (
                        "COMPLETED"
                        if call.ok
                        else "FAILED"
                    ),
                    "summary": (
                        call.result_summary
                    ),
                    "data": (
                        call.result_data
                    ),
                    "evidence_ids": [],
                }
            )

            for item in (
                call.evidence
            ):
                evidence_id = (
                    f"GE{len(evidence) + 1:03d}"
                )

                record = {
                    "evidence_id": evidence_id,
                    "kind": item.get(
                        "kind",
                        "TOOL_RESULT",
                    ),
                    "title": item.get(
                        "title",
                        call.name,
                    ),
                    "summary": item.get(
                        "summary",
                        call.result_summary
                        or call.name,
                    ),
                    "source": call.name,
                    "candidate_id": item.get(
                        "candidate_id"
                    ),
                    "severity": item.get(
                        "severity"
                    ),
                    "data": item,
                }

                evidence.append(
                    record
                )

            memory.remember(
                category=(
                    "TOOL_RESULT"
                ),
                content=(
                    call.result_summary
                    or (
                        f"{call.name} "
                        "completed."
                    )
                ),
                source=call.name,
                importance=(
                    "HIGH"
                    if call.ok
                    else "CRITICAL"
                ),
                data={
                    "arguments": (
                        call.arguments
                    ),
                    "ok": call.ok,
                    "error_code": (
                        call.error_code
                    ),
                },
            )

            if (
                call.result_data
                and call.name
                == "get_airspace_state"
            ):
                world_state = {
                    **world_state,
                    **call.result_data,
                }

        if questions:
            completed = sum(
                question.status
                == InvestigationStatus.COMPLETED
                for question
                in questions
            )

            completeness = (
                completed
                / len(questions)
            )
        else:
            completeness = 0.0

        plan = InvestigationPlan(
            objective=(
                "Use model-selected evidence to "
                "determine the operational cause "
                "and information required for intervention planning."
            ),
            questions=questions,
            completeness=max(
                completeness,
                quality.score,
            ),
            rationale=(
                "Questions correspond to dynamically "
                "requested investigation tools."
            ),
        )

        return InvestigationRunResult(
            execution=execution,
            quality=quality,
            world_state=world_state,
            investigation_plan=plan,
            investigation_results=(
                investigation_results
            ),
            evidence=evidence,
            working_memory=(
                memory.as_dicts()
            ),
        )

    def _load_initial_state(
        self,
    ) -> dict[str, Any]:
        result = (
            self.base_registry.invoke(
                "get_airspace_state"
            )
        )

        if not result.ok:
            return {}

        return result.data

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