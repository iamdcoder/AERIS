# AERIS API Reference

## 1. Running the API

From the repository root:

```bash
python -m uvicorn backend.app.api.app:app --reload
```

Interactive documentation is available at:

```text
GET /docs
GET /redoc
```

---

## 2. Health

### `GET /health`

Returns service liveness.

Example:

```json
{
  "status": "ok",
  "service": "aeris"
}
```

---

## 3. Airspace state

### `GET /airspace`

Returns the current full synthetic airspace snapshot.

The response contains the state consumed by the command center, including aircraft, sectors, airports, weather, restrictions and simulation time.

### `GET /flights/{flight_id}`

Returns a single aircraft/flight from the current airspace state.

Example:

```text
GET /flights/F102
```

### `GET /disruptions`

Returns active weather cells and restrictions plus the current simulation time.

Shape:

```json
{
  "weather_cells": [],
  "restrictions": [],
  "time_min": 19
}
```

### `GET /network/metrics`

Returns aggregate delay, aircraft counts, holding counts, per-sector utilization and airport operational data.

---

## 4. Deterministic decision API

### `POST /alternatives`

Generate deterministic candidates.

Request:

```json
{
  "flight_id": "F102"
}
```

Response:

```json
{
  "flight_id": "F102",
  "candidates": []
}
```

### `POST /validate`

Validate one candidate against hard constraints without applying it.

Minimum request fields:

```json
{
  "flight_id": "F102",
  "candidate_id": "ALT-D",
  "route": ["W3", "W5", "W7", "BOM"],
  "intervention_type": "reroute"
}
```

Optional fields include `speed_kt` and `cruise_altitude_ft`. Extra fields are currently permitted by the Pydantic request model to preserve compatibility with richer candidate objects.

### `POST /simulate`

Runs candidate-level network simulation.

Request shape is the same `CandidateRequest` structure.

### `POST /stress-test`

Runs deterministic future-state stress testing for a candidate.

### `POST /decision-score`

Scores and ranks candidate objects.

Request:

```json
{
  "candidates": [
    {
      "candidate_id": "ALT-D",
      "feasible": true
    }
  ]
}
```

### `POST /apply`

Applies an approved candidate intervention.

Request:

```json
{
  "candidate_id": "ALT-D",
  "approved": true
}
```

The API rejects `approved=false` with HTTP 403 because application requires explicit approval.

### `POST /verify`

Verifies the current applied intervention against the simulated state.

Request:

```json
{
  "candidate_id": "ALT-D"
}
```

---

## 5. Copilot API

### `POST /copilot/investigate`

Runs deterministic copilot investigation and prepares the decision pipeline.

Request defaults:

```json
{
  "target_flight_id": "F102",
  "scenario_id": "mumbai_weather_crisis",
  "run_id": "RUN-001"
}
```

### `POST /copilot/recommend`

Runs the hybrid investigation path. The current backend constructs a `RealEngineClient` and an `AgentOrchestrator` and returns the serialized `AgentState` after reaching the recommendation / human-approval boundary.

The hybrid path can use Gemini for investigation and falls back to deterministic investigation when Gemini is unavailable or insufficient.

### `POST /copilot/approve`

Approves the current stored run.

Request:

```json
{
  "run_id": "WEB-123",
  "decided_by": "demo_dispatcher"
}
```

### `POST /copilot/reject`

Rejects the current recommendation and requests reassessment.

Request:

```json
{
  "run_id": "WEB-123",
  "reason": "Operator requests a different network trade-off.",
  "decided_by": "demo_dispatcher"
}
```

### `POST /copilot/reset`

Resets the deterministic simulation state and clears the in-memory copilot run store.

---

## 6. Operational feed transport

### `WS /ws/operations`

Streams the isolated deterministic operational replay. The backend sends versioned snapshots when the replay changes and heartbeat payloads between changes.

### `GET /operations/live`

Returns the current replay snapshot and is the frontend polling fallback when WebSocket is unavailable.

The frontend should prefer WebSocket, reconnect when possible, and fall back to polling without changing the underlying operational state. This transport is a simulated hackathon feed, not a live AAI, airline, ATC or meteorological integration.

## 6. Error behavior

The API uses standard FastAPI HTTP errors for common invalid lifecycle operations.

Examples:

```text
404  Unknown run ID
403  Apply requested without explicit approval
409  Lifecycle conflict / execution error
422  Invalid request or deterministic validation input
500  Unexpected backend error
503  Copilot layer unavailable
```

The copilot layer also returns structured internal tool errors and records them in agent state rather than silently swallowing them.

---

## 7. API contract note

`contracts/api-contract.md` is the shared interface document. The current live operational transport is `WS /ws/operations`, with `GET /operations/live` as the polling fallback.

Both endpoints are implemented in the backend and read the same isolated operational replay state. Production deployments may set `VITE_OPERATIONS_WS_URL` explicitly when the frontend cannot derive the WebSocket URL from its API base URL.
