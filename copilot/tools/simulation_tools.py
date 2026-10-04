from typing import Any

from copilot.engine.client import EngineClient

from .base import AerisTool, ToolResult


class SimulateNetworkImpactTool(AerisTool):
    name = "simulate_network_impact"

    description = (
        "Run a counterfactual network simulation for a candidate "
        "intervention and return target and surrounding-network effects."
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
            self.engine.get_simulation_result(
                candidate_id
            )
        )

        if result is None:
            return ToolResult.failure(
                tool_name=self.name,
                error_code="SIMULATION_NOT_FOUND",
                error_message=(
                    f"No simulation result was found for "
                    f"{candidate_id}."
                ),
                summary=(
                    "Network simulation result is unavailable."
                ),
            )

        return ToolResult.success(
            tool_name=self.name,
            summary=(
                f"Network impact simulation completed for {candidate_id}."
            ),
            data=result,
            evidence=[
                {
                    "kind": "SIMULATION",
                    "title": (
                        f"{candidate_id} network impact"
                    ),
                    "summary": (
                        f"Predicted network delay delta: "
                        f"{result.get('network_delay_delta_min', 'N/A')} min."
                    ),
                    "candidate_id": candidate_id,
                }
            ],
        )


class GetNetworkMetricsTool(AerisTool):
    name = "get_network_metrics"

    description = (
        "Retrieve aggregate simulated network metrics for the "
        "current airspace state."
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
            "properties": {},
            "required": [],
        }

    def execute(
        self,
        **kwargs: Any,
    ) -> ToolResult:
        metrics = (
            self.engine.get_network_metrics()
        )

        return ToolResult.success(
            tool_name=self.name,
            summary=(
                "Current network metrics retrieved."
            ),
            data=metrics,
            evidence=[
                {
                    "kind": "NETWORK_METRICS",
                    "title": "Network metrics",
                    "summary": (
                        "Aggregate network-health metrics "
                        "are available for analysis."
                    ),
                }
            ],
        )


class ScoreCandidatesTool(AerisTool):
    """Request the engine's authoritative candidate ranking."""

    name = "score_candidates"
    description = "Score evaluated candidates using the deterministic engine's configured scoring model."

    def __init__(self, engine: EngineClient) -> None:
        self.engine = engine

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "candidate_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "IDs of candidates to evaluate and rank.",
                }
            },
            "required": ["candidate_ids"],
        }

    def execute(self, candidate_ids: list[str], **kwargs: Any) -> ToolResult:
        if not candidate_ids:
            return ToolResult.failure(
                tool_name=self.name,
                error_code="INVALID_ARGUMENTS",
                error_message="candidate_ids must contain at least one candidate ID.",
            )
        candidates = self.engine.score_candidates(candidate_ids)
        return ToolResult.success(
            tool_name=self.name,
            summary=f"The deterministic engine ranked {len(candidates)} candidate(s).",
            data={"candidates": candidates},
            evidence=[
                {
                    "kind": "ENGINE_SCORE",
                    "title": "Candidate ranking",
                    "summary": "Candidate ranking was calculated by the deterministic engine.",
                }
            ],
        )


def build_simulation_tools(
    engine: EngineClient,
) -> list[AerisTool]:
    return [
        SimulateNetworkImpactTool(engine),
        GetNetworkMetricsTool(engine),
        ScoreCandidatesTool(engine),
    ]