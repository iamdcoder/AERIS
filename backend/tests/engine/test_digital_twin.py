from app.engine.digital_twin.loaders import load_world
from app.engine.digital_twin.simulator import DigitalTwinSimulator


def test_flagship_has_40_aircraft():
    sim = DigitalTwinSimulator(load_world())
    assert len(sim.state.aircraft) == 40
    assert "F102" in sim.state.aircraft


def test_simulation_is_deterministic():
    a = DigitalTwinSimulator(load_world()).advance(15).snapshot()
    b = DigitalTwinSimulator(load_world()).advance(15).snapshot()
    assert a == b
