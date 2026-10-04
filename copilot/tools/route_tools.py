from typing import Any

from copilot.mock_engine import MockEngineClient

from .base import AerisTool, ToolResult


class GenerateAlternativesTool(AerisTool):
    name = "generate_alternatives"

    description = (
        "Generate deterministic operational intervention "
        "candidates for a target flight."
    )

    def __init__(
        self,
        engine: MockEngineClient,
    ) -> None:
        self.engine = engine

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "flight_id": {
                    "type": "string",
                    "description": "Target flight identifier.",
                }
            },
            "required": [
                "flight_id"
            ],
        }

    def execute(
        self,
        flight_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        candidates = (
            self.engine.get_alternatives(
                flight_id
            )
        )

        if not candidates:
            return ToolResult.failure(
                tool_name=self.name,
                error_code="NO_CANDIDATES",
                error_message=(
                    f"No intervention candidates were "
                    f"generated for {flight_id}."
                ),
                summary=(
                    "No intervention candidates are available."
                ),
            )

        return ToolResult.success(
            tool_name=self.name,
            summary=(
                f"Generated {len(candidates)} intervention "
                f"candidates for {flight_id}."
            ),
            data={
                "flight_id": flight_id,
                "alternatives": candidates,
            },
            evidence=[
                {
                    "kind": "CANDIDATE_SET",
                    "title": "Intervention candidates",
                    "summary": (
                        f"{len(candidates)} candidates generated "
                        "for evaluation."
                    ),
                }
            ],
        )


class ValidateCandidateTool(AerisTool):
    name = "validate_candidate"

    description = (
        "Validate one intervention candidate against "
        "the deterministic hard-constraint result."
    )

    def __init__(
        self,
        engine: MockEngineClient,
    ) -> None:
        self.engine = engine

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "candidate_id": {
                    "type": "string",
                    "description": (
                        "Identifier of the candidate to validate."
                    ),
                }
            },
            "required": [
                "candidate_id"
            ],
        }

    def execute(
        self,
        candidate_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        result = (
            self.engine.validate_candidate(
                candidate_id
            )
        )

        if result is None:
            return ToolResult.failure(
                tool_name=self.name,
                error_code="CANDIDATE_NOT_FOUND",
                error_message=(
                    f"Candidate {candidate_id} was not found."
                ),
                summary=(
                    "Candidate validation could not be performed."
                ),
            )

        feasible = result.get(
            "feasible"
        ) is True

        if feasible:
            return ToolResult.success(
                tool_name=self.name,
                summary=(
                    f"{candidate_id} passed hard-constraint validation."
                ),
                data=result,
                evidence=[
                    {
                        "kind": "CONSTRAINT",
                        "title": (
                            f"{candidate_id} validation passed"
                        ),
                        "summary": (
                            "Candidate passed the available "
                            "deterministic feasibility checks."
                        ),
                        "candidate_id": candidate_id,
                    }
                ],
            )

        reasons = result.get(
            "rejection_reasons",
            [],
        )

        return ToolResult.success(
            tool_name=self.name,
            summary=(
                f"{candidate_id} failed hard-constraint validation."
            ),
            data=result,
            evidence=[
                {
                    "kind": "CONSTRAINT",
                    "title": (
                        f"{candidate_id} rejected"
                    ),
                    "summary": (
                        "; ".join(reasons)
                        if reasons
                        else "Candidate failed a hard constraint."
                    ),
                    "candidate_id": candidate_id,
                    "severity": "HIGH",
                }
            ],
        )


def build_route_tools(
    engine: MockEngineClient,
) -> list[AerisTool]:
    return [
        GenerateAlternativesTool(engine),
        ValidateCandidateTool(engine),
    ]