# Future Features

The current hackathon build includes a deterministic live operational replay and live WebSocket/polling transport.

The next production-facing extensions are:

- authorized airline/AAI operational-data adapters;
- aviation weather adapters;
- NOTAM/restriction adapters;
- persistent operational state;
- authenticated WebSocket sessions;
- event replay persistence and audit history;
- richer airline network effects such as rotations, crew and passenger connections;
- confidence and uncertainty propagation from source data;
- multi-dispatcher collaboration.

The important architectural seam already exists:

```text
source adapter
    ↓
OperationalEvent
    ↓
OperationalStateStore
    ↓
AERIS engine / copilot
```

The hackathon replay is therefore a controlled stand-in for future authorized production feeds rather than a claim of direct access to those systems.
