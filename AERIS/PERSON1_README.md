# AERIS Person 1 — exact implementation pack

This pack implements the deterministic Airspace Intelligence Engine for the synthetic Mumbai Monsoon Network Crisis described in `scenarios/mumbai_weather_crisis.json`.

## Scope

Person 1 owns:

- `backend/app/models/**`
- `backend/app/engine/**`
- `backend/data/**`
- `backend/tests/engine/**`

Person 2 should consume `backend/app/engine/public.py` and should not import internal constraint/simulation modules directly.

## Scenario timeline

- T+0 baseline / F102 held at decision point
- T+5 convective weather expands near BOM
- T+8 BOM arrival capacity drops to 12
- T+10 holding begins for selected traffic
- T+12 S6 capacity is reduced to 6
- T+15 F102 becomes operationally degraded
- T+17 candidate generation
- T+18 temporary restriction activates
- T+19 two expected hard failures are ALT-C (restriction) and ALT-E (fuel)
- T+21 three feasible candidates are evaluated
- T+24 five future scenarios are stress-tested
- T+26 critic stage occurs on Person 2 side
- T+28 recommendation
- T+30 human approval / apply
- T+32 verification
- T+35 monitoring

## Intended candidate behavior

- `ALT-A`: shortest local route, feasible immediately, but intersects high weather and has poor future survival.
- `ALT-B`: moderate local option, avoids the main storm cell but relies on S6 and degrades under increased traffic.
- `ALT-C`: direct high-level option, rejected because R-MONSOON-01 covers its path at FL340.
- `ALT-D`: resilient sector-diversion option, avoids the main weather corridor and S6, and is expected to survive all five stress profiles.
- `ALT-E`: conservative long arc, rejected because it cannot preserve the configured 12-minute reserve.

## Run

From the repository root:

```bash
python scripts/test_person1_engine.py
pytest -q
```

## Integration rule

The engine is authoritative for hard feasibility. The LLM must not calculate fuel, capacity, conflict, restrictions, or physical validity. The agent calls `public.py` functions through its tool adapters and uses returned evidence to reason about interventions.

## Deliberate simplifications

This is a deterministic hackathon simulation, not a certified flight-management or ATC system. Coordinates, sector capacities, traffic, fuel and timing are synthetic. The simulation uses a 1.5x operational time scale so the 35-minute demo has meaningful in-flight state evolution. F102 is held at the decision point until the intervention is approved, which makes the route alternatives comparable from the same starting state.
