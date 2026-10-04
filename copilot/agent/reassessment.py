from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Set

from pydantic import BaseModel, Field

from copilot.agent.ranker import DecisionRanker, RankingSummary
from copilot.agent.scoring import DecisionScoreResult


class ReassessmentResult(BaseModel):
    rejected_candidate_id: str
    rejection_reason: str

    excluded_candidate_ids: List[str] = Field(
        default_factory=list
    )

    remaining_candidate_ids: List[str] = Field(
        default_factory=list
    )

    reranking_performed: bool = False

    new_recommended_candidate_id: Optional[str] = None

    decision_score_result: Optional[DecisionScoreResult] = None
    ranking_summary: Optional[RankingSummary] = None

    requires_new_approval: bool = False

    summary: str


class CandidateReassessor:
    """
    Re-ranks the remaining candidate set after human rejection.

    A rejected candidate is removed from future recommendations for
    the current decision cycle, while the historical rejection reason
    remains visible for auditability.

    The reassessor does not execute anything.
    """

    def __init__(
        self,
        ranker: Optional[DecisionRanker] = None,
    ) -> None:
        self.ranker = ranker or DecisionRanker()

    def reassess(
        self,
        rejected_candidate_id: str,
        rejection_reason: str,
        candidates: Iterable[Mapping[str, Any]],
        simulations: Optional[Any] = None,
        stress_tests: Optional[Any] = None,
        previously_rejected_ids: Optional[Iterable[str]] = None,
    ) -> ReassessmentResult:
        reason = rejection_reason.strip()

        if not reason:
            raise ValueError(
                "Reassessment requires the human rejection reason."
            )

        excluded: Set[str] = set(
            previously_rejected_ids or []
        )

        excluded.add(rejected_candidate_id)

        remaining = [
            dict(candidate)
            for candidate in candidates
            if self._candidate_id(candidate)
            not in excluded
        ]

        filtered_simulations = self._filter_results(
            results=simulations,
            excluded_ids=excluded,
        )

        filtered_stress_tests = self._filter_results(
            results=stress_tests,
            excluded_ids=excluded,
        )

        if not remaining:
            return ReassessmentResult(
                rejected_candidate_id=rejected_candidate_id,
                rejection_reason=reason,
                excluded_candidate_ids=sorted(excluded),
                remaining_candidate_ids=[],
                reranking_performed=False,
                new_recommended_candidate_id=None,
                decision_score_result=None,
                ranking_summary=None,
                requires_new_approval=False,
                summary=(
                    "Human rejected the recommendation and no "
                    "remaining candidate is available for reassessment."
                ),
            )

        score_result, ranking_summary = self.ranker.rank(
            candidates=remaining,
            simulations=filtered_simulations,
            stress_tests=filtered_stress_tests,
        )

        new_candidate_id = (
            ranking_summary.recommended_candidate_id
        )

        return ReassessmentResult(
            rejected_candidate_id=rejected_candidate_id,
            rejection_reason=reason,
            excluded_candidate_ids=sorted(excluded),
            remaining_candidate_ids=[
                self._candidate_id(candidate)
                for candidate in remaining
            ],
            reranking_performed=True,
            new_recommended_candidate_id=new_candidate_id,
            decision_score_result=score_result,
            ranking_summary=ranking_summary,
            requires_new_approval=(
                new_candidate_id is not None
            ),
            summary=self._build_summary(
                rejected_candidate_id=rejected_candidate_id,
                reason=reason,
                new_candidate_id=new_candidate_id,
                remaining_ids=[
                    self._candidate_id(candidate)
                    for candidate in remaining
                ],
            ),
        )

    @staticmethod
    def _candidate_id(
        candidate: Mapping[str, Any],
    ) -> str:
        for key in (
            "candidate_id",
            "id",
            "route_id",
            "alternative_id",
        ):
            value = candidate.get(key)

            if value is not None:
                return str(value)

        return "UNKNOWN"

    @classmethod
    def _filter_results(
        cls,
        results: Optional[Any],
        excluded_ids: Set[str],
    ) -> Any:
        if results is None:
            return None

        if isinstance(results, Mapping):
            if "candidates" in results:
                original = results["candidates"]

                if isinstance(original, list):
                    return {
                        **dict(results),
                        "candidates": [
                            item
                            for item in original
                            if (
                                isinstance(item, Mapping)
                                and cls._candidate_id(item)
                                not in excluded_ids
                            )
                        ],
                    }

            if "alternatives" in results:
                original = results["alternatives"]

                if isinstance(original, list):
                    return {
                        **dict(results),
                        "alternatives": [
                            item
                            for item in original
                            if (
                                isinstance(item, Mapping)
                                and cls._candidate_id(item)
                                not in excluded_ids
                            )
                        ],
                    }

            candidate_id = cls._candidate_id(results)

            if candidate_id in excluded_ids:
                return None

            return results

        if isinstance(results, list):
            return [
                item
                for item in results
                if (
                    isinstance(item, Mapping)
                    and cls._candidate_id(item)
                    not in excluded_ids
                )
            ]

        return results

    @staticmethod
    def _build_summary(
        rejected_candidate_id: str,
        reason: str,
        new_candidate_id: Optional[str],
        remaining_ids: List[str],
    ) -> str:
        if new_candidate_id is None:
            return (
                f"Human rejected {rejected_candidate_id}: "
                f"{reason}. Remaining candidates "
                f"({', '.join(remaining_ids)}) produced no "
                "feasible recommendation."
            )

        return (
            f"Human rejected {rejected_candidate_id}: "
            f"{reason}. AERIS reassessed the remaining candidates "
            f"and produced a new recommendation: "
            f"{new_candidate_id}."
        )