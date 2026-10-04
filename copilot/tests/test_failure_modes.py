import pytest

from copilot.agent.planner import (
    NoFeasibleCandidateError,
    select_initial_leader,
)


def test_no_feasible_candidates_fails_honestly():
    candidates = [
        {
            "candidate_id": "ALT-X",
            "feasible": False,
            "rejection_reasons": [
                "Fuel reserve below minimum"
            ],
        }
    ]

    with pytest.raises(
        NoFeasibleCandidateError,
        match="No safe candidate",
    ):
        select_initial_leader(
            candidates
        )