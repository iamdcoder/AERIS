from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any, Iterable, List, Mapping, Optional

from pydantic import BaseModel, Field

from copilot.agent.scoring import (
    CandidateDecisionScore,
    CandidateMetrics,
    DecisionScoreResult,
    DecisionScorer,
    ScoreComponents,
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
    ranked_candidates: List[RankedCandidate] = Field(default_factory=list)
    rationale: str


class DecisionRanker:
    """
    Rank candidate interventions without overriding engine feasibility.

    For normal unit-test payloads the existing copilot scorer is used.
    When the real deterministic engine attaches an authoritative candidate
    payload, those engine metrics become the source of truth for ranking and
    for candidate evidence shown to the UI.
    """

    def __init__(self, scorer: Optional[DecisionScorer] = None) -> None:
        self.scorer = scorer or DecisionScorer()

    def rank(
        self,
        candidates: Iterable[Mapping[str, Any]],
        simulations: Optional[Any] = None,
        stress_tests: Optional[Any] = None,
    ) -> tuple[DecisionScoreResult, RankingSummary]:
        candidate_list = [
            candidate if isinstance(candidate, dict) else dict(candidate)
            for candidate in candidates
        ]

        authoritative = self._index_authoritative_candidates(
            stress_tests
        )

        if authoritative:
            return self._rank_authoritative(
                candidate_list,
                authoritative,
            )

        result = self.scorer.score_candidates(
            candidates=candidate_list,
            simulations=simulations,
            stress_tests=stress_tests,
        )

        ranked = [
            {
                "item": next(
                    score
                    for score in result.scores
                    if score.candidate_id == candidate_id
                )
            }
            for candidate_id in result.ranked_candidate_ids
        ]

        ranked_candidates = [
            self._to_ranked_candidate(
                index,
                entry["item"],
            )
            for index, entry in enumerate(
                ranked,
                start=1,
            )
        ]

        return self._build_result_and_summary(
            result.scores,
            ranked_candidates,
            result,
        )

    def _rank_authoritative(
        self,
        candidates: List[Mapping[str, Any]],
        authoritative: Mapping[str, Mapping[str, Any]],
    ) -> tuple[DecisionScoreResult, RankingSummary]:
        scores: list[CandidateDecisionScore] = []

        for candidate in candidates:
            candidate_id = self._candidate_id(candidate)
            engine_candidate = authoritative.get(
                candidate_id
            )

            if engine_candidate is None:
                scores.append(
                    self._fallback_infeasible_score(
                        candidate
                    )
                )
                continue

            self._merge_authoritative_fields(
                candidate,
                engine_candidate,
            )

            scores.append(
                self._authoritative_score(
                    candidate,
                    engine_candidate,
                )
            )

        ranked_scores = sorted(
            scores,
            key=lambda item: (
                not item.feasible,
                -item.score if item.feasible else 0.0,
                self._network_ripple(item),
                item.candidate_id,
            ),
        )

        feasible = [
            score
            for score in ranked_scores
            if score.feasible
        ]

        best_score = (
            feasible[0].score
            if feasible
            else 0.0
        )

        best_local = self._best_local_score(
            feasible
        )

        for item in scores:
            item.decision_regret = round(
                max(
                    0.0,
                    best_score - item.score,
                ),
                4,
            )

            if item.raw_metrics.local_score is not None:
                item.local_regret = round(
                    max(
                        0.0,
                        best_local
                        - item.raw_metrics.local_score,
                    ),
                    4,
                )

        ranked_candidates = [
            self._to_ranked_candidate(
                index,
                item,
            )
            for index, item in enumerate(
                ranked_scores,
                start=1,
            )
        ]

        score_result = DecisionScoreResult(
            weights=self.scorer.weights,
            normalization=self.scorer.normalization,
            scores=scores,
            ranked_candidate_ids=[
                item.candidate_id
                for item in ranked_scores
            ],
            recommended_candidate_id=(
                feasible[0].candidate_id
                if feasible
                else None
            ),
        )

        return self._build_result_and_summary(
            scores,
            ranked_candidates,
            score_result,
        )

    def _build_result_and_summary(
        self,
        scores: List[CandidateDecisionScore],
        ranked_candidates: List[RankedCandidate],
        result: DecisionScoreResult,
    ) -> tuple[DecisionScoreResult, RankingSummary]:
        feasible = [
            candidate
            for candidate in ranked_candidates
            if candidate.feasible
        ]

        recommended_id = (
            feasible[0].candidate_id
            if feasible
            else None
        )

        runner_up_id = (
            feasible[1].candidate_id
            if len(feasible) > 1
            else None
        )

        score_gap = (
            round(
                feasible[0].score
                - feasible[1].score,
                4,
            )
            if len(feasible) > 1
            else 0.0
        )

        local_vs_global_flip = (
            self._detect_local_global_flip(
                feasible
            )
        )

        summary = RankingSummary(
            recommended_candidate_id=recommended_id,
            runner_up_candidate_id=runner_up_id,
            score_gap=score_gap,
            local_vs_global_flip=local_vs_global_flip,
            ranked_candidates=ranked_candidates,
            rationale=self._build_rationale(
                feasible_ranked=feasible,
                local_vs_global_flip=local_vs_global_flip,
                score_gap=score_gap,
            ),
        )

        result.recommended_candidate_id = (
            recommended_id
        )

        return result, summary

    def _authoritative_score(
        self,
        candidate: Mapping[str, Any],
        engine_candidate: Mapping[str, Any],
    ) -> CandidateDecisionScore:
        candidate_id = self._candidate_id(
            engine_candidate
        )

        feasible = bool(
            engine_candidate.get(
                "feasible",
                candidate.get(
                    "feasible",
                    False,
                ),
            )
        )

        network = self._mapping(
            engine_candidate.get(
                "network_metrics"
            )
        )

        resilience = self._mapping(
            engine_candidate.get(
                "resilience_metrics"
            )
        )

        validation = self._mapping(
            engine_candidate.get(
                "constraint_results"
            )
        )

        fuel = self._mapping(
            validation.get("fuel")
        )

        stress = self._mapping(
            engine_candidate.get(
                "stress_report"
            )
        )

        target_delay = self._number(
            engine_candidate.get(
                "target_delay_min"
            )
        )

        added_distance = self._number(
            engine_candidate.get(
                "added_distance_km"
            )
        )

        network_delay = self._number(
            engine_candidate.get(
                "network_delay_delta_min"
            )
        )

        peak = self._number(
            engine_candidate.get(
                "max_sector_utilization_pct"
            )
        )

        affected = self._integer(
            engine_candidate.get(
                "affected_flights"
            )
        )

        reserve = self._number(
            (
                engine_candidate.get(
                    "fuel_reserve_margin_min"
                )
                if "fuel_reserve_margin_min"
                in engine_candidate
                else fuel.get(
                    "reserve_margin_min"
                )
            )
        )

        future = self._clamp(
            self._number(
                resilience.get(
                    "future_robustness"
                ),
                0.0,
            )
            or 0.0
        )

        reintervention = self._clamp(
            self._number(
                resilience.get(
                    "reintervention_probability"
                ),
                0.0,
            )
            or 0.0
        )

        passed = self._integer(
            stress.get("passed")
        )

        total = self._integer(
            stress.get("total")
        )

        local_score = self._derive_local_score(
            target_delay,
            added_distance,
        )

        metrics = CandidateMetrics(
            candidate_id=candidate_id,
            feasible=feasible,
            target_delay_min=target_delay,
            added_distance_km=added_distance,
            fuel_margin_kg=self._number(
                engine_candidate.get(
                    "fuel_margin_kg"
                )
            ),
            affected_flights=affected,
            network_delay_delta_min=network_delay,
            peak_sector_utilization=(
                peak / 100.0
                if peak is not None
                and peak > 2
                else peak
            ),
            network_resilience=future,
            stress_passed=passed,
            stress_total=total,
            second_intervention_probability=(
                reintervention
            ),
            local_score=local_score,
            rejection_reasons=list(
                engine_candidate.get(
                    "rejection_reasons",
                    [],
                )
                or []
            ),
        )

        if feasible:
            target_component = self._clamp(
                self._number(
                    network.get(
                        "target_flight_benefit"
                    ),
                    0.0,
                )
                / 12.0
            )

            ripple_cost = (
                self._number(
                    network.get(
                        "network_ripple_cost"
                    ),
                    0.0,
                )
                or 0.0
            )

            network_impact = self._clamp(
                1.0
                - ripple_cost / 15.0
            )

            fuel_component = self._clamp(
                (reserve or 0.0) / 30.0
            )

            resilience_component = self._clamp(
                future
                * (1.0 - reintervention)
            )

            components = ScoreComponents(
                target_flight_benefit=(
                    target_component
                ),
                network_resilience=(
                    resilience_component
                ),
                network_impact_score=(
                    network_impact
                ),
                fuel_safety_margin=(
                    fuel_component
                ),
                future_robustness=future,
            )

            score = self._number(
                engine_candidate.get(
                    "decision_score"
                )
            )

            if score is None:
                score = self._weighted_score(
                    components
                )

        else:
            components = ScoreComponents(
                target_flight_benefit=0.0,
                network_resilience=0.0,
                network_impact_score=0.0,
                fuel_safety_margin=0.0,
                future_robustness=0.0,
            )

            score = 0.0

        explanation = (
            self._authoritative_explanation(
                candidate_id=candidate_id,
                score=score,
                target_delay=target_delay,
                network_delay=network_delay,
                peak=peak,
                future=future,
                reintervention=reintervention,
                survival_passed=passed,
                survival_total=total,
                feasible=feasible,
                rejection_reasons=(
                    metrics.rejection_reasons
                ),
            )
        )

        return CandidateDecisionScore(
            candidate_id=candidate_id,
            feasible=feasible,
            score=round(
                self._clamp(score),
                4,
            ),
            components=components,
            raw_metrics=metrics,
            second_intervention_probability=(
                reintervention
            ),
            explanation=explanation,
        )

    def _fallback_infeasible_score(
        self,
        candidate: Mapping[str, Any],
    ) -> CandidateDecisionScore:
        candidate_id = self._candidate_id(
            candidate
        )

        return CandidateDecisionScore(
            candidate_id=candidate_id,
            feasible=False,
            score=0.0,
            components=ScoreComponents(
                target_flight_benefit=0.0,
                network_resilience=0.0,
                network_impact_score=0.0,
                fuel_safety_margin=0.0,
                future_robustness=0.0,
            ),
            raw_metrics=CandidateMetrics(
                candidate_id=candidate_id,
                feasible=False,
                rejection_reasons=list(
                    candidate.get(
                        "rejection_reasons",
                        [],
                    )
                    or []
                ),
            ),
            second_intervention_probability=1.0,
            explanation=(
                f"{candidate_id} is infeasible under "
                "the deterministic engine's hard constraints."
            ),
        )

    @staticmethod
    def _index_authoritative_candidates(
        stress_tests: Optional[Any],
    ) -> dict[str, dict[str, Any]]:
        if stress_tests is None:
            return {}

        if isinstance(
            stress_tests,
            Mapping,
        ):
            if "results" in stress_tests:
                stress_tests = (
                    stress_tests["results"]
                )
            elif "stress_tests" in stress_tests:
                stress_tests = (
                    stress_tests["stress_tests"]
                )
            else:
                stress_tests = [
                    stress_tests
                ]

        if (
            not isinstance(
                stress_tests,
                Iterable,
            )
            or isinstance(
                stress_tests,
                (str, bytes),
            )
        ):
            return {}

        indexed: dict[
            str,
            dict[str, Any],
        ] = {}

        for item in stress_tests:
            if not isinstance(
                item,
                Mapping,
            ):
                continue

            authoritative = item.get(
                "authoritative_candidate"
            )

            if (
                isinstance(
                    authoritative,
                    Mapping,
                )
                and authoritative.get(
                    "candidate_id"
                )
                is not None
            ):
                indexed[
                    str(
                        authoritative[
                            "candidate_id"
                        ]
                    )
                ] = dict(
                    authoritative
                )

        return indexed

    @staticmethod
    def _merge_authoritative_fields(
        candidate: Mapping[str, Any],
        engine_candidate: Mapping[str, Any],
    ) -> None:
        if not isinstance(
            candidate,
            dict,
        ):
            return

        network = (
            DecisionRanker._mapping(
                engine_candidate.get(
                    "network_metrics"
                )
            )
        )

        resilience = (
            DecisionRanker._mapping(
                engine_candidate.get(
                    "resilience_metrics"
                )
            )
        )

        stress = (
            DecisionRanker._mapping(
                engine_candidate.get(
                    "stress_report"
                )
            )
        )

        candidate.update(
            {
                "feasible": engine_candidate.get(
                    "feasible",
                    candidate.get(
                        "feasible",
                        False,
                    ),
                ),
                "decision_score": engine_candidate.get(
                    "decision_score"
                ),
                "target_delay_min": engine_candidate.get(
                    "target_delay_min"
                ),
                "added_distance_km": engine_candidate.get(
                    "added_distance_km"
                ),
                "fuel_reserve_margin_min": engine_candidate.get(
                    "fuel_reserve_margin_min"
                ),
                "affected_flights": engine_candidate.get(
                    "affected_flights"
                ),
                "network_delay_delta_min": engine_candidate.get(
                    "network_delay_delta_min"
                ),
                "max_sector_utilization_pct": engine_candidate.get(
                    "max_sector_utilization_pct"
                ),
                "resilience_score": resilience.get(
                    "future_robustness"
                ),
                "future_robustness": resilience.get(
                    "future_robustness"
                ),
                "second_intervention_probability": resilience.get(
                    "reintervention_probability"
                ),
                "stress_survival": {
                    "passed": stress.get(
                        "passed",
                        0,
                    ),
                    "total": stress.get(
                        "total",
                        0,
                    ),
                },
                "score_explanation": engine_candidate.get(
                    "score_explanation"
                ),
                "network_metrics": deepcopy(
                    network
                ),
                "resilience_metrics": deepcopy(
                    resilience
                ),
                "stress_report": deepcopy(
                    stress
                ),
            }
        )

    @staticmethod
    def _best_local_score(
        scores: List[
            CandidateDecisionScore
        ],
    ) -> float:
        values = [
            score.raw_metrics.local_score
            for score in scores
            if score.raw_metrics.local_score
            is not None
        ]

        return (
            max(values)
            if values
            else 0.0
        )

    @staticmethod
    def _network_ripple(
        item: CandidateDecisionScore,
    ) -> float:
        value = (
            item.raw_metrics
            .network_delay_delta_min
        )

        return (
            value
            if value is not None
            else float("inf")
        )

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
            target_delay_min=(
                metrics.target_delay_min
            ),
            network_delay_delta_min=(
                metrics.network_delay_delta_min
            ),
            peak_sector_utilization=(
                metrics.peak_sector_utilization
            ),
            affected_flights=(
                metrics.affected_flights
            ),
            resilience=(
                components.network_resilience
            ),
            future_robustness=(
                components.future_robustness
            ),
            second_intervention_probability=(
                item.second_intervention_probability
            ),
            explanation=item.explanation,
        )

    @staticmethod
    def _detect_local_global_flip(
        candidates: List[RankedCandidate],
    ) -> bool:
        if len(candidates) < 2:
            return False

        if any(
            item.local_regret > 0.0
            for item in candidates
        ):
            local_best = sorted(
                candidates,
                key=lambda item: (
                    item.local_regret,
                    item.candidate_id,
                ),
            )[0]
        else:
            local_best = sorted(
                candidates,
                key=lambda item: (
                    (
                        item.target_delay_min
                        if item.target_delay_min
                        is not None
                        else float("inf")
                    ),
                    item.candidate_id,
                ),
            )[0]

        return (
            local_best.candidate_id
            != candidates[0].candidate_id
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
                f"{winner.candidate_id} is the only "
                "feasible candidate."
            )
        else:
            runner = feasible_ranked[1]

            base = (
                f"{winner.candidate_id} leads with an "
                f"AERIS score of {winner.score:.2f}, "
                f"ahead of {runner.candidate_id} at "
                f"{runner.score:.2f} "
                f"(gap {score_gap:.2f})."
            )

        if local_vs_global_flip:
            base += (
                " The locally strongest option is not "
                "the network-level winner, demonstrating "
                "the multi-objective behavior of AERIS."
            )

        if winner.future_robustness >= 0.8:
            base += (
                " The leading candidate also has strong "
                "future-scenario robustness."
            )

        if (
            winner.second_intervention_probability
            <= 0.2
        ):
            base += (
                " Its estimated second-intervention "
                "probability is low."
            )

        return base

    @staticmethod
    def _authoritative_explanation(
        *,
        candidate_id: str,
        score: float,
        target_delay: Optional[float],
        network_delay: Optional[float],
        peak: Optional[float],
        future: float,
        reintervention: float,
        survival_passed: Optional[int],
        survival_total: Optional[int],
        feasible: bool,
        rejection_reasons: List[str],
    ) -> str:
        if not feasible:
            reasons = "; ".join(
                rejection_reasons
            )

            return (
                f"{candidate_id} is infeasible. "
                "Deterministic blockers: "
                f"{reasons or 'hard constraint failure'}."
            )

        target_text = (
            f"{target_delay:.2f} min"
            if target_delay is not None
            else "unavailable"
        )

        network_text = (
            f"{network_delay:+.2f} min"
            if network_delay is not None
            else "unavailable"
        )

        peak_text = (
            f"{peak:.1f}%"
            if peak is not None
            else "unavailable"
        )

        stress_text = (
            f"{survival_passed}/{survival_total}"
            if (
                survival_passed is not None
                and survival_total is not None
            )
            else "unknown"
        )

        return (
            f"{candidate_id}: deterministic engine "
            f"score {score:.2f}; target impact "
            f"{target_text}; network impact "
            f"{network_text}; peak sector utilization "
            f"{peak_text}; stress survival "
            f"{stress_text}; future robustness "
            f"{future:.0%}; estimated re-intervention "
            f"probability {reintervention:.0%}."
        )

    def _weighted_score(
        self,
        components: ScoreComponents,
    ) -> float:
        weights = self.scorer.weights

        return round(
            self._clamp(
                weights.target_flight_benefit
                * components.target_flight_benefit
                + weights.network_resilience
                * components.network_resilience
                + weights.network_impact_score
                * components.network_impact_score
                + weights.fuel_safety_margin
                * components.fuel_safety_margin
                + weights.future_robustness
                * components.future_robustness
            ),
            4,
        )

    @staticmethod
    def _derive_local_score(
        target_delay: Optional[float],
        added_distance: Optional[float],
    ) -> Optional[float]:
        if (
            target_delay is None
            and added_distance is None
        ):
            return None

        target_component = (
            (
                1.0
                - target_delay / 15.0
            )
            if target_delay is not None
            else 0.5
        )

        distance_component = (
            (
                1.0
                - added_distance / 250.0
            )
            if added_distance is not None
            else 0.5
        )

        return round(
            0.70
            * max(
                0.0,
                min(
                    1.0,
                    target_component,
                ),
            )
            + 0.30
            * max(
                0.0,
                min(
                    1.0,
                    distance_component,
                ),
            ),
            4,
        )

    @staticmethod
    def _candidate_id(
        candidate: Optional[Mapping[str, Any]],
    ) -> str:
        if candidate is None:
            return "UNKNOWN"

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

    @staticmethod
    def _mapping(
        value: Any,
    ) -> dict[str, Any]:
        return (
            dict(value)
            if isinstance(
                value,
                Mapping,
            )
            else {}
        )

    @staticmethod
    def _number(
        value: Any,
        default: float | None = None,
    ) -> float | None:
        if value is None:
            return default

        try:
            parsed = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return default

        return (
            parsed
            if isfinite(parsed)
            else default
        )

    @staticmethod
    def _integer(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:
        if not isfinite(value):
            return 0.0

        return max(
            0.0,
            min(
                1.0,
                value,
            ),
        )