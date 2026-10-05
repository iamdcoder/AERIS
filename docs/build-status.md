# AERIS Build Status

## Current verified build

### Deterministic engine and Copilot

- The complete repository Python test suite passes.
- The flagship agent path is reproducible and stops at human approval.
- The flagship recommendation is produced by the actual deterministic engine and agent logic.
- Human approval executes the selected intervention and verification returns `VERIFIED`.
- Rejection produces a fresh recommendation and returns to the human-approval gate.

### Runtime

- FastAPI starts from the repository root with the canonical import path.
- `GET /health` returns HTTP 200.
- Copilot REST endpoints are operational.
- The operational replay no longer mutates the authoritative decision engine.

### Operational data layer

- Canonical `OperationalEvent` contract implemented.
- Thread-safe `OperationalStateStore` implemented.
- Deterministic minute-by-minute operational replay implemented.
- Replay state is isolated from the authoritative AERIS engine.
- Historical simulation chronology is preserved through `simulation_time_min` and event timestamps.
- REST live-feed endpoints implemented.
- WebSocket `/ws/operations` implemented.
- Browser polling fallback implemented.
- `OperationalEventSource` interface provides the boundary for future authorized external adapters.

### Frontend

- Vite `/api` development proxy configured.
- Production API/WebSocket configuration remains explicit and environment-driven.
- Backend health indicator uses the real `/health` endpoint.
- Stale Copilot runs are handled without claiming success.
- Live operational feed panel is available in the command center.
- Typography/readability pass is applied.
- WebSocket reconnect lifecycle cleans up old sockets and prevents duplicate reconnect loops.
- Header action semantics distinguish an active run from a pending human decision.

## Verification performed in this environment

```text
Repository Python suite: 407 passed, 5 skipped
Backend suite:           286 passed
Copilot suite:           121 passed, 5 skipped
Agent flagship runner:   SUCCESS
Live replay runner:      SUCCESS through T+35
FastAPI /health:         HTTP 200
FastAPI /operations/live: HTTP 200
Python compileall:       PASS
```

The frontend production bundle could not be rebuilt in this environment because npm dependency installation could not complete without registry access. The committed frontend source and lockfile were preserved; run the normal frontend build on a machine with npm registry access:

```bash
cd frontend
npm ci
npm run build
```

## Hackathon limitation

Copilot runs remain process-local/in-memory. Restarting the backend invalidates active `run_id` values. The frontend detects this stale-run condition and returns to a safe state instead of reporting a false approval or rejection.

The live operational feed is a deterministic simulation/replay. It is intentionally not represented as privileged production access to AAI, airline, ATC, or meteorological systems.
