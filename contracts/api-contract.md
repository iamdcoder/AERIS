# AERIS API Contract — v0.1

## Integration rule

The deterministic engine is authoritative for operational feasibility. The agent orchestrates investigation and synthesis but never invents safety-critical calculations.

## Read endpoints

```text
GET  /health
GET  /airspace
GET  /flights/{flight_id}
GET  /disruptions
GET  /network/metrics
```

## Decision endpoints

```text
POST /alternatives
POST /validate
POST /simulate
POST /stress-test
POST /decision-score
POST /apply
POST /verify
POST /copilot/investigate
POST /copilot/recommend
WS   /ws/airspace
```

## Candidate response minimum

```json
{
  "candidate_id": "ALT-D",
  "flight_id": "F102",
  "intervention_type": "reroute",
  "route": ["W1", "W7", "W11", "W15"],
  "feasible": true,
  "constraint_results": {},
  "target_delay_min": 8,
  "added_distance_km": 42,
  "fuel_reserve_margin_min": 48,
  "affected_flights": 1,
  "network_delay_delta_min": -14,
  "max_sector_utilization_pct": 82,
  "stress_survival": {"passed": 5, "total": 5},
  "decision_score": 0.91,
  "reintervention_probability": 0.08,
  "regret": 0.11,
  "rejection_reasons": []
}
```

## Decision package minimum

```json
{
  "target_flight_id": "F102",
  "recommendation": "ALT-D",
  "confidence": 0.91,
  "summary": "Slightly slower locally, substantially more resilient network outcome.",
  "evidence": [],
  "alternatives": [],
  "critic": {},
  "human_approval_required": true,
  "status": "AWAITING_APPROVAL"
}
```

## Status values

Use stable uppercase values across backend, agent and frontend:

```text
OBSERVING
DIAGNOSING
GENERATING
VALIDATING
SIMULATING
STRESS_TESTING
CRITIQUING
RECOMMENDING
AWAITING_APPROVAL
APPROVED
REJECTED
EXECUTING
VERIFIED
REASSESSMENT_REQUIRED
NO_FEASIBLE_OPTION
DEGRADED
```
