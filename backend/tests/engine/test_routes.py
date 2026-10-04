from app.engine.digital_twin.loaders import load_world
from app.engine.routes.generator import generate_candidate_routes


def test_five_distinct_candidates():
    state = load_world()
    candidates = generate_candidate_routes(state.graph, "F102")
    assert [c["candidate_id"] for c in candidates] == ["ALT-A", "ALT-B", "ALT-C", "ALT-D", "ALT-E"]
    assert len({tuple(c["route"]) for c in candidates}) == 5
    assert all(c["route_valid"] for c in candidates)
