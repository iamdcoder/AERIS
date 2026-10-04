from typing import Any, Mapping


class NoFeasibleCandidateError(RuntimeError):
    pass


def feasible_candidates(
    candidates: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        dict(candidate)
        for candidate in candidates
        if candidate.get("feasible") is True
    ]


def rejected_candidates(
    candidates: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        dict(candidate)
        for candidate in candidates
        if candidate.get("feasible") is not True
    ]


def select_initial_leader(
    candidates: list[Mapping[str, Any]],
) -> dict[str, Any]:
    feasible = feasible_candidates(candidates)

    if not feasible:
        raise NoFeasibleCandidateError(
            "No safe candidate satisfies current hard constraints."
        )

    ranked = sorted(
        feasible,
        key=lambda candidate: float(
            candidate.get(
                "local_score",
                candidate.get("decision_score", 0.0),
            )
        ),
        reverse=True,
    )

    return ranked[0]


def select_post_critic_candidate(
    candidates: list[Mapping[str, Any]],
    challenged_candidate_id: str | None,
) -> dict[str, Any]:
    feasible = feasible_candidates(candidates)

    if not feasible:
        raise NoFeasibleCandidateError(
            "No safe candidate remains after evaluation."
        )

    alternatives = [
        candidate
        for candidate in feasible
        if candidate.get("candidate_id") != challenged_candidate_id
    ]

    pool = alternatives or feasible

    ranked = sorted(
        pool,
        key=lambda candidate: float(
            candidate.get("decision_score", 0.0)
        ),
        reverse=True,
    )

    return ranked[0]
