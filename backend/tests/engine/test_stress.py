from app.engine.digital_twin.loaders import load_world
from app.engine.digital_twin.simulator import DigitalTwinSimulator
from app.engine.routes.generator import generate_candidate_routes
from app.engine.stress_test.report import summarize_stress_test
from app.engine.stress_test.runner import run_stress_test


def test_stress_report_is_repeatable():
    sim = DigitalTwinSimulator(load_world())
    sim.advance(21)
    candidate = [c for c in generate_candidate_routes(sim.state.graph, "F102") if c["candidate_id"] == "ALT-D"][0]
    a = summarize_stress_test(run_stress_test(sim.state, candidate))
    b = summarize_stress_test(run_stress_test(sim.state, candidate))
    assert a == b
    assert a["total"] == 5
