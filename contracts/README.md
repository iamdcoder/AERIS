# AERIS Contracts

The `contracts/` directory is the integration boundary between the deterministic engine, copilot/API layer and future consumers.

## Files

```text
contracts/
├── api-contract.md
├── flight.schema.json
├── sector.schema.json
├── airport.schema.json
├── weather.schema.json
├── restriction.schema.json
├── alternative.schema.json
├── simulation.schema.json
├── scenario.schema.json
├── decision.schema.json
├── verification.schema.json
└── examples/
```

## Rules

1. Freeze field names after integration.
2. Do not silently change response shapes.
3. Update contracts and dependent tests together.
4. Keep synthetic example payloads valid JSON.
5. Document planned interfaces separately from implemented interfaces.

## Current transport note

`api-contract.md` includes a planned `WS /ws/airspace` interface. The current backend source does not implement a WebSocket route yet; REST is the implemented transport.
