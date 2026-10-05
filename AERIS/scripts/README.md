# AERIS Scripts

All commands below are run from the repository root.

## `run_flagship.py`

Deterministic offline proof of the main Mumbai Monsoon scenario.

```bash
python scripts/run_flagship.py
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

## `run_agent_flagship.py`

End-to-end proof of the observable agent loop and human-control boundary.

```bash
python scripts/run_agent_flagship.py
```

It verifies the local-vs-network decision, critic challenge, recommendation gate, approval, simulated execution, verification, and rejection/reassessment fail-closed behavior.

## `run_live_replay.py`

Replay the deterministic operational event stream through T+35.

```bash
python scripts/run_live_replay.py --stop-at 35
```

The script prints simulation-time events and stops automatically at the requested checkpoint.

## `preflight_submission.py`

Run the complete submission gate from the repository root.

```bash
python scripts/preflight_submission.py
```

The preflight checks Python compilation, backend/copilot tests, both flagship proofs, the full deterministic operational replay, API/REST/WebSocket reachability, frontend regression tests, documentation consistency, and submission hygiene. The Vite build is reported as `BLOCKED BY ENVIRONMENT` when frontend dependencies are unavailable rather than being treated as a false pass.

## `test_person1_engine.py`

Small developer smoke test for the deterministic engine layer.
