# Deterministic Airspace Engine

## 1. Purpose

The deterministic engine is the operational authority inside AERIS. It models a synthetic airspace network and provides reproducible calculations for route feasibility, network consequences, future-state stress, scoring, application and verification.

The engine is deliberately deterministic for the flagship scenario. This makes the hackathon demonstration reproducible and makes regression tests meaningful.

---

## 2. Engine structure

```text
backend/app/engine/
│
├── digital_twin/
│   ├── state.py
│   ├── loaders.py
│   └── simulator.py
│
├── constraints/
│   ├── weather.py
│   ├── fuel.py
│   ├── performance.py
│   ├── capacity.py
│   ├── conflict.py
│   ├── restriction.py
│   └── validator.py
│
├── routes/
│   ├── graph.py
│   ├── generator.py
│   └── interventions.py
│
├── simulation/
│   ├── network.py
│   ├── cascades.py
│   └── transitions.py
│
├── stress_test/
│   ├── scenarios.py
│   ├── runner.py
│   └── report.py
│
├── metrics/
│   ├── network.py
│   ├── resilience.py
│   └── score.py
│
└── public.py
```

---

## 3. Digital twin

The synthetic digital twin tracks:

- aircraft state;
- route progress;
- sectors and capacity;
- airports and arrival acceptance;
- weather cells;
- temporary restrictions;
- network delay.

The simulator advances the scenario in deterministic time steps and applies scenario events at defined timestamps.

---

## 4. Route generation

The engine creates multiple deterministic intervention candidates for the target flight.

For the flagship decision snapshot, the route candidates are:

```text
ALT-A
W3 → W10 → W11 → BOM

ALT-B
W3 → W5 → W6 → W8 → W11 → W12 → BOM

ALT-C
W3 → W5 → W10 → W11 → W12 → BOM

ALT-D
W3 → W5 → W7 → BOM

ALT-E
W3 → W5 → W7 → W9 → W8 → W11 → W12 → BOM
```

The exact routes are synthetic and scenario-specific.

---

## 5. Hard constraints

A candidate is not considered operationally feasible merely because it produces a good score.

The validator evaluates deterministic constraints including:

### Weather

Checks candidate interaction with active weather cells and preserves the weather-risk evidence associated with the route.

### Fuel

Estimates candidate route distance/time and verifies that remaining fuel stays above the required reserve threshold.

For the flagship scenario, ALT-E is rejected because it cannot preserve the configured reserve margin.

### Aircraft performance

Checks speed and altitude against aircraft capabilities. A degraded aircraft is subject to the configured degraded performance ceiling.

For the flagship scenario, ALT-C is rejected because its FL340 path conflicts with the active temporary restriction / degraded-performance conditions.

### Sector capacity

Projects candidate traffic through relevant sectors and checks capacity headroom and utilization.

### Conflict / separation

Checks candidate consequences against simulated surrounding aircraft and the configured minimum separation.

### Restrictions

Rejects candidates that enter an active restriction in a prohibited way.

### Airport pressure

Considers arrival pressure at the destination airport during the degraded-capacity window.

---

## 6. Decision context and frozen snapshots

`backend/app/engine/public.py` maintains a decision context so validation, simulation and stress testing can be tied to the same decision snapshot.

This is important because the candidate should be evaluated against the state that existed when the decision was made rather than against a later state that could have changed while downstream work was running.

The public facade exposes a context ID and snapshot metadata.

Example shape:

```text
Decision snapshot
    |
    +--> target state
    +--> candidate definitions
    +--> validation results
    +--> simulation results
    +--> stress results
```

Candidate identity is preserved across these operations.

---

## 7. Network simulation

The engine does not stop at the target aircraft.

Candidate simulation estimates:

- target-flight impact;
- affected aircraft;
- network delay delta;
- sector pressure / peak utilization;
- other downstream network consequences.

The flagship comparison illustrates the effect:

```text
ALT-A: target +0.03 min, network +22.03 min
ALT-B: target +15.38 min, network +55.38 min
ALT-D: target +4.49 min, network +12.49 min
```

The network delta is therefore a first-class decision metric rather than a decorative chart.

---

## 8. Stress testing

The stress engine evaluates candidates against deterministic future perturbations.

Current flagship profiles:

```text
F1  Weather expansion +10%
F2  Weather expansion +20%
F3  S6 capacity -15% with future bypass restriction
F4  Traffic demand +15%
F5  BOM acceptance -20%
```

Observed flagship outcome:

```text
ALT-A  0/5
ALT-B  0/5
ALT-D  4/5
```

This is the basis for the future-resilience portion of the decision.

---

## 9. Decision score

The deterministic scorer combines normalized components using fixed weights.

```text
target flight benefit  25%
network resilience     25%
network impact score   20%
fuel safety margin     15%
future robustness      15%
```

The score is only meaningful after operational feasibility has been established by the engine.

---

## 10. Public facade rules

Other modules should use:

```text
backend/app/engine/public.py
```

rather than importing internal engine modules directly.

This allows the engine implementation to evolve without breaking the agent/API layer and provides a single protected integration boundary.

---

## 11. Apply and verify

Application is separate from recommendation.

```text
candidate generated
      ↓
validated
      ↓
simulated
      ↓
stress-tested
      ↓
recommended
      ↓
human approval
      ↓
apply intervention
      ↓
verify state
```

The engine's `/apply` API refuses requests with `approved=false`.

---

## 12. Current simulation scope

The engine is synthetic and scenario-driven. It is suitable for a deterministic hackathon environment, not for operational deployment.

No claim should be made that the synthetic geometry, aircraft performance, capacities, route graph, weather model or delay model reproduces real Indian airspace or certified aviation behavior.
