# Scripts

Reserved for small deterministic developer utilities.

Keep scripts dependency-light: do not move engine or agent logic here.

---

## `run_flagship.py` — Deterministic Flagship Proof

The single-command reproducible proof of the complete AERIS engine lifecycle
for the Mumbai Monsoon Multi-Constraint Network Crisis scenario.

### Usage

Run from the repository root:

```bash
PYTHONPATH=backend .venv/bin/python scripts/run_flagship.py
```

Or, if your shell has the venv active and `backend/` on PYTHONPATH:

```bash
python scripts/run_flagship.py
```

### What it does

Executes the exact timeline from `scenarios/mumbai_weather_crisis.json`
through the public engine facade (`backend/app/engine/public.py`):

```
T+00  BASELINE            — 40 aircraft, BOM capacity 18, F102 AIRBORNE
T+05  WEATHER             — WX-BOM-01 convective cell, intensity HIGH
T+08  BOM CAPACITY DROP   — arrival capacity 18 → 12 arr/hr
T+10  HOLDING BEGINS      — affected flights accumulate delay
T+12  S6 CAPACITY CUT     — bypass sector at limit
T+15  F102 DEGRADED       — status DEGRADED, fuel 50 min remaining
T+17  CANDIDATES          — ALT-A/B/C/D/E generated deterministically
T+18  RESTRICTION         — R-MONSOON-01 activates over FL340 corridor
T+19  VALIDATION          — ALT-C rejected (restriction), ALT-E rejected (fuel)
T+21  SIMULATION          — network impact for ALT-A, ALT-B, ALT-D
T+24  STRESS TEST         — 5 future scenarios for each feasible candidate
T+26  CRITIC              — preliminary leader challenged
T+28  RECOMMENDATION      — ALT-D selected (resilient sector-diversion)
T+30  HUMAN APPROVAL      — explicit gate; approved = YES; apply called
T+32  VERIFICATION        — engine verifies intervention is holding
T+35  MONITORING          — final airspace state reported
```

### Properties

- **Deterministic**: identical output on every run after `reset_engine()`
- **Offline**: no network calls, no LLM, no random numbers
- **Authoritative**: all feasibility logic comes from the engine, never the runner
- **Honest failures**: exits non-zero if any assertion fails or apply is rejected

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Flagship completed successfully |
| 1 | Verification returned a non-success status |
| 2 | Story assertion failed (engine did not match scenario specification) |

---

## `test_person1_engine.py`

Quick developer smoke-test for the constraint validation and scoring layer.
Runs directly without pytest.
