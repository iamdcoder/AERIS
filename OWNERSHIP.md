# AERIS Ownership and Integration Boundaries

## Historical two-person ownership model

The repository was originally divided into two major ownership islands.

### Harsh — Airspace Intelligence Engineer

Primary area:

```text
backend/app/engine/**
backend/app/models/**
backend/data/**
backend/tests/engine/**
```

Typical responsibilities:

- digital twin;
- aircraft / sector / airport state;
- weather and restrictions;
- route graph and candidate generation;
- fuel and performance constraints;
- conflict detection;
- sector capacity;
- network simulation;
- stress testing;
- deterministic metrics;
- engine execution / verification state.

### Devansh — Agent + Product Engineer

Primary area:

```text
copilot/**
frontend/**
backend/app/api/**
backend/tests/api/**
```

Typical responsibilities:

- agent orchestration;
- investigation;
- tool adapters;
- planner / scorer / ranker;
- critic;
- synthesis;
- evidence / observability;
- human approval and reassessment;
- frontend dashboard;
- candidate comparison;
- verification presentation.

---

## Protected engine boundary

The intended cross-module boundary is:

```text
backend/app/engine/public.py
```

Agent/API code should consume stable public operations or explicit client adapters instead of importing private engine internals.

---

## Shared coordination zones

```text
contracts/**
scenarios/**
docs/**
README.md
CONTRIBUTING.md
OWNERSHIP.md
.env.example
```

Contract or scenario changes should be treated as coordinated integration work.

---

## Current single-developer state

The project may now be maintained by one developer even though the repository structure preserves the original separation. The ownership document is retained because the separation still helps protect interfaces and makes the architecture understandable to future contributors.
