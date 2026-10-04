# AERIS Architecture

```text
Frontend
   ↓ REST + WebSocket
Backend API adapters
   ↓ stable engine facade
backend.app.engine.public
   ↓
Deterministic airspace engine

Gemini / AgentOrchestrator
   ↓
Copilot tools
   ↓
EngineClient (RealEngineClient)
   ↓
backend.app.engine.public
```

The deterministic engine is the operational-feasibility authority. The agent selects tools, gathers evidence, compares candidates, challenges the recommendation and requests human approval. Copilot production defaults to `RealEngineClient`; its only engine dependency is the public facade. `MockEngineClient` is test/offline-only and must be explicitly injected. Gemini cannot invoke apply/verify actions; application code must obtain human approval before calling those adapter operations.
