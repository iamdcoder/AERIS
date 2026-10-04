# AERIS Architecture

```text
Frontend
   ↓ REST + WebSocket
Backend API adapters
   ↓ stable engine facade
Deterministic airspace engine  ←→  scenario/stress-test engine
   ↑
Agent tools
   ↑
Agent orchestrator + critic
```

The deterministic engine is the operational-feasibility authority. The agent selects tools, gathers evidence, compares candidates, challenges the recommendation and requests human approval.
