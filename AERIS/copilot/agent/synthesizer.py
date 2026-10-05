from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field

from copilot.agent.critic import CriticResult
from copilot.agent.ranker import RankingSummary
from copilot.agent.scoring import (
    CandidateDecisionScore,
    DecisionScoreResult,
)


class RecommendationEvidence(BaseModel):
    category: str
    statement: str
    source: str


class FinalRecommendation(BaseModel):
    candidate_id: Optional[str]

    decision: str
    confidence: float

    requires_human_approval: bool = True

    target_flight_id: Optional[str] = None

    target_delay_min: Optional[float] = None
    network_delay_delta_min: Optional[float] = None
    peak_sector_utilization: Optional[float] = None
    affected_flights: Optional[int] = None

    resilience: Optional[float] = None
    future_robustness: Optional[float] = None
    second_intervention_probability: Optional[float] = None

    local_vs_global_flip: bool = False
    critic_challenged: bool = False
    critic_summary: str = ""

    evidence: List[RecommendationEvidence] = Field(
        default_factory=list
    )

    explanation: str


class DecisionSynthesizer:
    """
    Final deterministic decision synthesizer.

    It combines:
      - score/ranking evidence;
      - critic findings;
      - raw simulation evidence.

    The synthesizer never executes an intervention.
    It only produces a recommendation which remains subject to
    explicit human approval.
    """

    def synthesize(
        self,
        ranking: RankingSummary,
        score_result: DecisionScoreResult,
        critic_result: CriticResult,
        target_flight_id: Optional[str] = None,
    ) -> FinalRecommendation:
        score_map = {
            item.candidate_id: item
            for item in score_result.scores
        }

        selected_id = self._select_candidate(
            ranking=ranking,
            score_map=score_map,
            critic_result=critic_result,
        )

        if selected_id is None:
            return FinalRecommendation(
                candidate_id=None,
                decision="NO_SAFE_RECOMMENDATION",
                confidence=0.0,
                requires_human_approval=True,
                target_flight_id=target_flight_id,
                critic_challenged=critic_result.challenged,
                critic_summary=critic_result.summary,
                evidence=[
                    RecommendationEvidence(
                        category="FEASIBILITY",
                        statement=(
                            "No feasible candidate survived the "
                            "decision process."
                        ),
                        source="deterministic ranking",
                    )
                ],
                explanation=(
                    "AERIS cannot produce a safe recommendation "
                    "from the available candidates."
                ),
            )

        selected = score_map[selected_id]

        confidence = self._confidence(
            selected=selected,
            ranking=ranking,
            critic_result=critic_result,
        )

        evidence = self._build_evidence(
            selected=selected,
            ranking=ranking,
            critic_result=critic_result,
        )

        explanation = self._build_explanation(
            selected=selected,
            ranking=ranking,
            critic_result=critic_result,
        )

        return FinalRecommendation(
            candidate_id=selected.candidate_id,
            decision="RECOMMEND",
            confidence=confidence,
            requires_human_approval=True,
            target_flight_id=target_flight_id,
            target_delay_min=(
                selected.raw_metrics.target_delay_min
            ),
            network_delay_delta_min=(
                selected.raw_metrics.network_delay_delta_min
            ),
            peak_sector_utilization=(
                selected.raw_metrics.peak_sector_utilization
            ),
            affected_flights=(
                selected.raw_metrics.affected_flights
            ),
            resilience=(
                selected.components.network_resilience
            ),
            future_robustness=(
                selected.components.future_robustness
            ),
            second_intervention_probability=(
                selected.second_intervention_probability
            ),
            local_vs_global_flip=(
                ranking.local_vs_global_flip
            ),
            critic_challenged=critic_result.challenged,
            critic_summary=critic_result.summary,
            evidence=evidence,
            explanation=explanation,
        )

    @staticmethod
    def _select_candidate(
        ranking: RankingSummary,
        score_map: Dict[str, CandidateDecisionScore],
        critic_result: CriticResult,
    ) -> Optional[str]:
        leader_id = ranking.recommended_candidate_id

        if leader_id is None:
            return None

        leader = score_map.get(leader_id)

        if leader is None or not leader.feasible or not leader.recommendable:
            return None

        if (
            critic_result.should_reconsider
            and critic_result.replacement_candidate_id
        ):
            replacement = score_map.get(
                critic_result.replacement_candidate_id
            )

            if (
                replacement is not None
                and replacement.feasible
                and replacement.recommendable
            ):
                return replacement.candidate_id

        return leader.candidate_id

    @staticmethod
    def _confidence(
        selected: CandidateDecisionScore,
        ranking: RankingSummary,
        critic_result: CriticResult,
    ) -> float:
        base = 0.55

        if selected.components.future_robustness >= 0.80:
            base += 0.15

        if selected.components.network_resilience >= 0.80:
            base += 0.10

        if selected.second_intervention_probability <= 0.20:
            base += 0.08

        if ranking.score_gap >= 0.10:
            base += 0.06
        elif ranking.score_gap >= 0.05:
            base += 0.03

        if critic_result.challenged:
            if critic_result.should_reconsider:
                base -= 0.15
            else:
                base -= 0.03

        if (
            selected.raw_metrics.network_delay_delta_min
            is not None
            and selected.raw_metrics.network_delay_delta_min < 0
        ):
            base += 0.03

        return round(
            max(
                0.0,
                min(
                    0.99,
                    base,
                ),
            ),
            2,
        )

    @staticmethod
    def _build_evidence(
        selected: CandidateDecisionScore,
        ranking: RankingSummary,
        critic_result: CriticResult,
    ) -> List[RecommendationEvidence]:
        metrics = selected.raw_metrics
        components = selected.components

        evidence = [
            RecommendationEvidence(
                category="DECISION_SCORE",
                statement=(
                    f"AERIS score is {selected.score:.2f}."
                ),
                source="deterministic decision scorer",
            ),
            RecommendationEvidence(
                category="TARGET_IMPACT",
                statement=(
                    DecisionSynthesizer._format_optional(
                        "Target delay",
                        metrics.target_delay_min,
                        " min",
                    )
                ),
                source="candidate/simulation evidence",
            ),
            RecommendationEvidence(
                category="NETWORK_IMPACT",
                statement=(
                    DecisionSynthesizer._format_optional(
                        "Network delay delta",
                        metrics.network_delay_delta_min,
                        " min",
                    )
                ),
                source="network simulation",
            ),
            RecommendationEvidence(
                category="NETWORK_RESILIENCE",
                statement=(
                    f"Network resilience component is "
                    f"{components.network_resilience:.0%}."
                ),
                source="deterministic decision scorer",
            ),
            RecommendationEvidence(
                category="FUTURE_ROBUSTNESS",
                statement=(
                    f"Future robustness is "
                    f"{components.future_robustness:.0%}."
                ),
                source="stress-test evidence",
            ),
            RecommendationEvidence(
                category="REINTERVENTION",
                statement=(
                    f"Estimated second-intervention probability "
                    f"is {selected.second_intervention_probability:.0%}."
                ),
                source="stress-test evidence / deterministic proxy",
            ),
        ]

        if ranking.local_vs_global_flip:
            evidence.append(
                RecommendationEvidence(
                    category="LOCAL_VS_GLOBAL",
                    statement=(
                        "The locally attractive candidate differs "
                        "from the network-level winner."
                    ),
                    source="deterministic ranking",
                )
            )

        if critic_result.challenged:
            evidence.append(
                RecommendationEvidence(
                    category="CRITIC",
                    statement=critic_result.summary,
                    source="deterministic critic",
                )
            )

        return evidence

    @staticmethod
    def _build_explanation(
        selected: CandidateDecisionScore,
        ranking: RankingSummary,
        critic_result: CriticResult,
    ) -> str:
        metrics = selected.raw_metrics

        target_phrase = (
            f"{metrics.target_delay_min:.0f} min target delay"
            if metrics.target_delay_min is not None
            else "unknown target delay"
        )

        network_phrase = (
            f"{metrics.network_delay_delta_min:+.0f} min "
            "network delay change"
            if metrics.network_delay_delta_min is not None
            else "unknown network impact"
        )

        robustness_phrase = (
            f"{selected.components.future_robustness:.0%} "
            "future robustness"
        )

        if critic_result.challenged:
            critic_phrase = (
                " The critic explicitly challenged the preliminary "
                "leader before this recommendation was finalized."
            )
        else:
            critic_phrase = (
                " The critic found no material failure condition "
                "in the evaluated evidence."
            )

        if ranking.local_vs_global_flip:
            local_phrase = (
                " The network-level winner is not the locally "
                "highest-scoring option."
            )
        else:
            local_phrase = ""

        return (
            f"AERIS recommends {selected.candidate_id} based on "
            f"{target_phrase}, {network_phrase}, and "
            f"{robustness_phrase}.{critic_phrase}"
            f"{local_phrase} Human approval is required before execution."
        )

    @staticmethod
    def _format_optional(
        label: str,
        value: Optional[float],
        suffix: str,
    ) -> str:
        if value is None:
            return f"{label}: unavailable"

        return f"{label}: {value:.1f}{suffix}"