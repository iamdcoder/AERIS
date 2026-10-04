# AERIS Ownership & Isolation Rules

The repository is intentionally divided so two developers can build in parallel with minimal merge conflicts.

## Person 1 — Airspace Intelligence Engineer

### Write access

```text
backend/app/engine/**
backend/app/models/**
backend/data/**
backend/tests/engine/**
```

### Read-only dependencies

```text
contracts/**
scenarios/**
backend/app/api/**
```

### Owns

Digital twin, aircraft/sector/airport state, weather/restrictions, route graph and generation, deterministic hard constraints, fuel/performance checks, conflict detection, sector capacity, network simulation, stress testing, metrics, execution state and verification state.

## Person 2 — Agent + Product Engineer

### Write access

```text
copilot/**
frontend/**
backend/app/api/**
backend/tests/api/**
copilot/tests/**
```

### Read-only dependencies

```text
contracts/**
scenarios/**
backend/app/engine/public.py
backend/app/models/**
backend/data/**
```

### Owns

Agent orchestration, tool adapters, planner/critic/synthesizer, evidence trail, API endpoints, WebSocket adapter, dashboard, map, candidate comparison, approval flow, timeline and verification presentation.

## Shared / coordinated files

```text
contracts/**
scenarios/**
docs/**
README.md
CONTRIBUTING.md
.gitignore
.env.example
```

After Phase 0, contract changes require both developers to agree, update fixtures/mocks/tests, and communicate the change before merging.

## Protected integration boundary

Person 1 exposes stable engine functions through:

```text
backend/app/engine/public.py
```

Person 2 should call the public facade or API adapters rather than importing route/constraint internals.

Person 2 must not modify engine algorithms to make the UI work. Person 1 must not modify API/UI code to expose engine results.
