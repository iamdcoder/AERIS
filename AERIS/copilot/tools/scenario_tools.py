from typing import Any

from copilot.engine.client import EngineClient

from .base import AerisTool, ToolResult


class StressTestCandidateTool(AerisTool):
    name = "stress_test_candidate"

    description = (
        "Evaluate a candidate intervention across deterministic "
        "future-state perturbation scenarios."
    )

    def __init__(
        self,
        engine: EngineClient,
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
                        "Candidate intervention identifier."
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
            self.engine.get_stress_test_result(
                candidate_id
            )
        )

        if result is None:
            return ToolResult.failure(
                tool_name=self.name,
                error_code="STRESS_RESULT_NOT_FOUND",
                error_message=(
                    f"No stress-test result was found "
                    f"for {candidate_id}."
                ),
                summary=(
                    "Future-state robustness evidence is unavailable."
                ),
            )

        passed = int(
            result.get(
                "passed",
                0,
            )
        )

        total = int(
            result.get(
                "total",
                0,
            )
        )

        if result.get("survival_pct") is not None:
            survival = float(result["survival_pct"]) / 100.0
        else:
            # Backward compatibility with the test-only legacy fixture shape.
            survival = passed / total if total > 0 else 0.0

        warnings = []

        if survival < 0.80:
            warnings.append(
                (
                    f"{candidate_id} survives only "
                    f"{passed}/{total} stress scenarios."
                )
            )

        return ToolResult.success(
            tool_name=self.name,
            summary=(
                f"Stress testing completed for {candidate_id}: "
                f"{passed}/{total} scenarios passed."
            ),
            data={
                **result,
                "survival_ratio": survival,
            },
            warnings=warnings,
            evidence=[
                {
                    "kind": "STRESS_TEST",
                    "title": (
                        f"{candidate_id} future robustness"
                    ),
                    "summary": (
                        f"Scenario survival: "
                        f"{passed}/{total}."
                    ),
                    "candidate_id": candidate_id,
                    "severity": (
                        "HIGH"
                        if survival < 0.60
                        else "MEDIUM"
                        if survival < 0.80
                        else "LOW"
                    ),
                }
            ],
        )


def build_scenario_tools(
    engine: EngineClient,
) -> list[AerisTool]:
    return [
        StressTestCandidateTool(engine),
    ]