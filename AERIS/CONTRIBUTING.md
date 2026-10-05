# Contributing to AERIS

AERIS was initially structured for two developers working in parallel. The original ownership model remains documented in `OWNERSHIP.md`.

## Repository principles

1. Keep the deterministic engine authoritative for operational calculations.
2. Keep the agent/API layer separated from engine internals through `backend/app/engine/public.py` and adapters.
3. Preserve candidate IDs and contract response shapes.
4. Prefer complete, testable vertical slices over unrelated features.
5. Do not silently replace a deterministic result with an LLM-generated number.
6. Keep human approval explicit.
7. Keep the flagship scenario deterministic.
8. Update documentation whenever an API, lifecycle stage, contract, or safety boundary changes.

## Commit style

Use small, descriptive commits:

```text
feat(engine): add sector capacity model
feat(agent): add candidate evaluation tool
feat(ui): add recommendation panel
fix(engine): correct fuel reserve check
fix(agent): handle rejected candidate
docs: add judge demo guide
```

## Contract discipline

Shared contracts live under `contracts/`.

Do not casually rename fields or change response shapes after integration. When a contract changes:

```text
update contract
    ↓
update dependent code
    ↓
update fixtures / mocks
    ↓
update tests
    ↓
run full regression
    ↓
document the change
```

## Documentation standards

Technical documentation should distinguish clearly between:

- implemented behavior;
- deterministic synthetic behavior;
- planned features;
- external assumptions.

Do not describe a planned WebSocket or live-data integration as implemented until the corresponding backend and frontend code exists and is tested.

## Before merging

Run:

```bash
python -m pytest backend/tests -q
python -m pytest copilot/tests -q
```

Then:

```bash
cd frontend
npm run build
```

For core engine changes, also run:

```bash
cd ..
python scripts/run_flagship.py
```
