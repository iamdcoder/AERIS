# Backend ownership

Person 1 owns the deterministic engine and domain models.
Person 2 owns the API adapters.

The engine is the authority for feasibility and network simulation. API modules translate the stable engine facade into contract-compliant HTTP/WebSocket responses.
