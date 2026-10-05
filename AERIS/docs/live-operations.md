# AERIS Live Operational Data Layer

## What the hackathon build does

AERIS now contains a deterministic **operational-event replay layer** that behaves like a live normalized feed.

It is intentionally not presented as a direct connection to production AAI, airline, ATC or meteorological systems.

The replay publishes the same canonical event shape that future authorized adapters can use.

```text
Scenario / external adapter
        |
        v
OperationalEvent
        |
        v
OperationalStateStore
        |
        v
Current airspace snapshot
        |
        +--> REST
        |
        +--> WebSocket
        |
        v
AERIS dashboard
```

## Event categories

The normalized contract supports:

- `SURVEILLANCE_UPDATE`
- `WEATHER_UPDATE`
- `SECTOR_CAPACITY_UPDATE`
- `AIRPORT_CAPACITY_UPDATE`
- `TRAFFIC_UPDATE`
- `RESTRICTION_UPDATE`
- `FLIGHT_STATE_UPDATE`
- `DISRUPTION_DETECTED`
- `DISRUPTION_CLEARED`
- `SYSTEM_ALERT`

Every event contains an ID, monotonic sequence, event type, source, timestamp, simulation time, entity identity, severity and flexible payload.

## Deterministic replay

The flagship Mumbai scenario is replayed one simulated minute at a time.

The browser demo can replay the operational timeline through T+35. The flagship AERIS decision point remains T+19; events after that point demonstrate continued monitoring after a decision is prepared or verified.

The replay therefore provides an observable sequence such as:

```text
T+00 baseline
T+01 surveillance update
T+05 weather update
T+08 airport capacity update
T+10 traffic / holding update
T+12 sector capacity update
T+15 F102 degradation
T+18 restriction update
T+19 surveillance + operational state updates
```

The exact event list is derived from the deterministic engine scenario so the live display remains reproducible.

## REST interface

```text
GET  /operations/live
GET  /operations/events?limit=20

POST /operations/replay/reset
POST /operations/replay/start
POST /operations/replay/stop
POST /operations/replay/step
```

`/operations/live` returns the normalized operational store plus the replay-owned digital-twin snapshot under:

```text
entities.airspace.CURRENT
```

The replay snapshot is intentionally isolated from the authoritative decision engine. It is an operational-data simulation, not the source of truth for candidate feasibility or execution.

## WebSocket interface

```text
WS /ws/operations
```

The socket streams the current operational snapshot when the state version changes and sends heartbeat messages while unchanged.

The frontend automatically falls back to REST polling if WebSocket transport is unavailable.

## Authority boundary

The event layer is a **data-ingestion and observability layer**.

It does not calculate:

- route feasibility
- fuel safety
- conflict separation
- network score
- resilience score
- intervention execution

Those remain the responsibility of the deterministic AERIS engine.

## Production evolution

The intended future path is:

```text
AAI / airline / weather / airport adapters
                    |
                    v
             Canonical events
                    |
                    v
         OperationalStateStore
                    |
                    v
              AERIS engine
                    |
                    v
             agentic copilot
```

The replay can then be removed without changing the normalized event contract consumed by the rest of the system. Production adapters should implement `OperationalEventSource` and publish the same `OperationalEvent` schema.

## Live reassessment in the dashboard

When the simulated feed advances beyond the flagship decision point at T+19, the command center exposes **REASSESS CURRENT CONDITIONS**. That action takes the current replay minute, rebuilds the authoritative deterministic decision snapshot at that same minute, and runs the existing AERIS recommendation pipeline against the new state.

The live replay remains isolated while the authoritative engine creates the new decision snapshot. This prevents an operational-data update from mutating an in-progress decision context.
