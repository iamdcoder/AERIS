from typing import Any, Mapping

from .planner import select_post_critic_candidate
from .state import CriticResult, Recommendation


def build_recommendation(
    candidates: list[Mapping[str, Any]],
    critic_result: CriticResult,
    evidence_ids: list[str],
) -> Recommendation:
    selected = select_post_critic_candidate(
        candidates,
        challenged_candidate_id=(
            critic_result.candidate_id
            if critic_result.challenged
            else None
        ),
    )

    candidate_id = str(
        selected["candidate_id"]
    )

    resilience = float(
        selected.get(
            "resilience_score",
            0.0,
        )
    )

    confidence = float(
        selected.get(
            "confidence",
            resilience,
        )
    )

    rejected = []

    for candidate in candidates:
        if candidate.get(
            "candidate_id"
        ) == candidate_id:
            continue

        if candidate.get(
            "feasible"
        ) is not True:
            rejected.append(
                {
                    "candidate_id": candidate.get(
                        "candidate_id"
                    ),
                    "reason": candidate.get(
                        "rejection_reasons",
                        [],
                    ),
                }
            )

    why_selected = [
        (
            f"Network-resilience score: "
            f"{resilience:.2f}"
        ),
        (
            f"Scenario survival: "
            f"{selected.get('scenario_survival', 'N/A')}"
        ),
        (
            f"Network delay delta: "
            f"{selected.get('network_delay_delta_min', 'N/A')} min"
        ),
    ]

    summary = str(
        selected.get(
            "recommendation_summary",
            (
                "Selected because it provides "
                "the strongest resilient outcome "
                "among the surviving candidates."
            ),
        )
    )

    return Recommendation(
        candidate_id=candidate_id,
        confidence=confidence,
        summary=summary,
        why_selected=why_selected,
        rejected_candidates=rejected,
        critic=critic_result,
        evidence_ids=evidence_ids,
        human_approval_required=True,
    )
