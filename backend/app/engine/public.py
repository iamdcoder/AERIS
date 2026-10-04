"""Stable integration facade owned by Person 1.

Person 2 should depend on these public functions/contracts, not internal engine modules.
"""


def get_airspace_state():
    raise NotImplementedError("Implement in the engine branch")


def generate_alternatives(flight_id: str):
    raise NotImplementedError("Implement in the engine branch")


def validate_candidate(candidate: dict):
    raise NotImplementedError("Implement in the engine branch")


def simulate_candidate(candidate: dict):
    raise NotImplementedError("Implement in the engine branch")


def stress_test_candidate(candidate: dict):
    raise NotImplementedError("Implement in the engine branch")


def score_candidates(candidates: list[dict]):
    raise NotImplementedError("Implement in the engine branch")


def apply_intervention(candidate_id: str):
    raise NotImplementedError("Implement in the engine branch")


def verify_state(candidate_id: str):
    raise NotImplementedError("Implement in the engine branch")
