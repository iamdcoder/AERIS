from app.engine.constraints.validator import validate_candidate
from app.engine.digital_twin.loaders import load_world
from app.engine.digital_twin.simulator import DigitalTwinSimulator
from app.engine.routes.generator import generate_candidate_routes


def test_flagship_has_expected_two_hard_failures_at_19():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(19)
    candidates = generate_candidate_routes(sim.state.graph, "F102")
    results = {c["candidate_id"]: validate_candidate(sim.state, c) for c in candidates}
    assert results["ALT-C"]["feasible"] is False
    assert results["ALT-E"]["feasible"] is False
    assert results["ALT-A"]["feasible"] is True
    assert results["ALT-B"]["feasible"] is True
    assert results["ALT-D"]["feasible"] is True
