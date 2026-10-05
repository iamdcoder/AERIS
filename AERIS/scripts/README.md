# AERIS Scripts

## `run_flagship.py`

Deterministic offline proof of the main Mumbai Monsoon scenario.

Run from the repository root:

```bash
PYTHONPATH=backend python scripts/run_flagship.py
```

The runner:

1. resets the deterministic engine;
2. advances the scenario through its timeline;
3. generates the five candidate interventions;
4. validates the candidate set;
5. creates a frozen decision context;
6. simulates the feasible candidates;
7. stress-tests future scenarios;
8. scores and ranks candidates;
9. applies the recommended candidate after explicit scripted approval;
10. verifies the resulting state;
11. prints a machine-readable summary.

The runner is offline and does not call Gemini.

## `test_person1_engine.py`

Small developer smoke test for the deterministic engine layer.
