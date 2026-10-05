# AERIS Backend

The `backend/` directory contains the FastAPI transport layer, domain models, deterministic airspace engine, scenario data and backend tests.

## Run

From the repository root:

Linux / macOS:
```bash
python -m uvicorn backend.app.api.app:app --host 127.0.0.1 --port 8000
```

Windows (PowerShell / CMD):
```powershell
python -m uvicorn backend.app.api.app:app --host 127.0.0.1 --port 8000
```

Alternative (all OS):
```bash
python backend/main.py
```

Note: Run the backend as a single worker process (`workers=1`, default) because hackathon copilot run state is maintained in-memory by `run_id`.

FastAPI docs:

```text
http://127.0.0.1:8000/docs
```

## Structure

```text
backend/
├── app/api/
│   ├── routes/
│   │   ├── health.py
│   │   ├── airspace.py
│   │   ├── decisions.py
│   │   └── copilot.py
│   └── schemas/
├── app/engine/
│   ├── digital_twin/
│   ├── constraints/
│   ├── routes/
│   ├── simulation/
│   ├── stress_test/
│   ├── metrics/
│   └── public.py
├── app/models/
├── data/
└── tests/
```

## API principle

The API is a transport and orchestration layer. The deterministic engine remains authoritative for feasibility and simulation.

## Engine principle

Other modules should use `backend/app/engine/public.py` rather than importing private engine modules directly.

## Tests

From repository root:

```bash
python -m pytest backend/tests -q
```

The latest user-verified backend suite completed with 272 passed and one deprecation warning from the test client dependency stack.
