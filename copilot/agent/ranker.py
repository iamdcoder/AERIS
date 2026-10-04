from __future__ import annotations

from typing import Any, Iterable, List, Mapping, Optional

from pydantic import BaseModel, Field

from copilot.agent.scoring import (
    CandidateDecisionScore,
    DecisionScoreResult,
    DecisionScorer,
)


class RankedCandidate(BaseModel):
    rank: int
    candidate_id: str
    feasible: bool
    score: float
    decision_regret: float
    local_regret: float

    target_delay_min: Optional[float] = None
    network_delay_delta_min: Optional[float] = None
    peak_sector_utilization: Optional[float] = None
    affected_flights: Optional[int] = None

    resilience: float
    future_robustness: float
    second_intervention_probability: float

    explanation: str


class RankingSummary(BaseModel):
    recommended_candidate_id: Optional[str] = None
    runner_up_candidate_id: Optional[str] = None

    score_gap: float = 0.0
    local_vs_global_flip: bool = False

    ranked_candidates: List[RankedCandidate] = Field(
        default_factory=list
    )

    rationale: str


class DecisionRanker:
    """
    Deterministic ranking layer on top of DecisionScorer.

    The ranker does not override feasibility. Infeasible candidates
    remain visible for auditability but can never become the recommendation.
    """

    def __init__(
        self,
        scorer: Optional[DecisionScorer] = None,
    ) -> None:
        self.scorer = scorer or DecisionScorer()

    def rank(
        self,
        candidates: Iterable[Mapping[str, Any]],
        simulations: Optional[Any] = None,
        stress_tests: Optional[Any] = None,
    ) -> tuple[DecisionScoreResult, RankingSummary]:
        result = self.scorer.score_candidates(
            candidates=candidates,
            simulations=simulations,
            stress_tests=stress_tests,
        )

        score_map = {
            score.candidate_id: score
            for score in result.scores
        }

        ranked_scores = [
            score_map[candidate_id]
            for candidate_id in result.ranked_candidate_ids
        ]

        ranked_candidates: List[RankedCandidate] = []

        for rank, item in enumerate(
            ranked_scores,
            start=1,
        ):
            ranked_candidates.append(
                self._to_ranked_candidate(
                    rank=rank,
                    item=item,
                )
            )

        feasible_ranked = [
            item
            for item in ranked_candidates
            if item.feasible
        ]

        recommended_id = (
            feasible_ranked[0].candidate_id
            if feasible_ranked
            else None
        )

        runner_up_id = (
            feasible_ranked[1].candidate_id
            if len(feasible_ranked) > 1
            else None
        )

        score_gap = 0.0

        if len(feasible_ranked) > 1:
            score_gap = round(
                feasible_ranked[0].score
                - feasible_ranked[1].score,
                4,
            )

        local_vs_global_flip = (
            self._detect_local_global_flip(
                feasible_ranked
            )
        )

        rationale = self._build_rationale(
            feasible_ranked=feasible_ranked,
            local_vs_global_flip=local_vs_global_flip,
            score_gap=score_gap,
        )

        summary = RankingSummary(
            recommended_candidate_id=recommended_id,
            runner_up_candidate_id=runner_up_id,
            score_gap=score_gap,
            local_vs_global_flip=local_vs_global_flip,
            ranked_candidates=ranked_candidates,
            rationale=rationale,
        )

        result.recommended_candidate_id = recommended_id

        return result, summary

    @staticmethod
    def _to_ranked_candidate(
        rank: int,
        item: CandidateDecisionScore,
    ) -> RankedCandidate:
        metrics = item.raw_metrics
        components = item.components

        return RankedCandidate(
            rank=rank,
            candidate_id=item.candidate_id,
            feasible=item.feasible,
            score=item.score,
            decision_regret=item.decision_regret,
            local_regret=item.local_regret,
            target_delay_min=metrics.target_delay_min,
            network_delay_delta_min=metrics.network_delay_delta_min,
            peak_sector_utilization=metrics.peak_sector_utilization,
            affected_flights=metrics.affected_flights,
            resilience=components.network_resilience,
            future_robustness=components.future_robustness,
            second_intervention_probability=(
                item.second_intervention_probability
            ),
            explanation=item.explanation,
        )

    @staticmethod
    def _detect_local_global_flip(
        ranked_candidates: List[RankedCandidate],
    ) -> bool:
        if len(ranked_candidates) < 2:
            return False

        local_best = sorted(
            ranked_candidates,
            key=lambda item: (
                item.local_regret,
                item.candidate_id,
            ),
        )[0]

        global_best = ranked_candidates[0]

        return (
            local_best.candidate_id
            != global_best.candidate_id
        )

    @staticmethod
    def _build_rationale(
        feasible_ranked: List[RankedCandidate],
        local_vs_global_flip: bool,
        score_gap: float,
    ) -> str:
        if not feasible_ranked:
            return (
                "No feasible candidate is available. "
                "AERIS must not recommend an intervention."
            )

        winner = feasible_ranked[0]

        if len(feasible_ranked) == 1:
            base = (
                f"{winner.candidate_id} is the only feasible "
                "candidate."
            )

        else:
            runner_up = feasible_ranked[1]

            base = (
                f"{winner.candidate_id} leads with an AERIS score "
                f"of {winner.score:.2f}, ahead of "
                f"{runner_up.candidate_id} at "
                f"{runner_up.score:.2f} "
                f"(gap {score_gap:.2f})."
            )

        if local_vs_global_flip:
            base += (
                " The locally strongest option is not the "
                "network-level winner, demonstrating the "
                "multi-objective behavior of AERIS."
            )

        if winner.future_robustness >= 0.8:
            base += (
                " The leading candidate also has strong "
                "future-scenario robustness."
            )

        if winner.second_intervention_probability <= 0.2:
            base += (
                " Its estimated second-intervention probability "
                "is low."
            )

        return base