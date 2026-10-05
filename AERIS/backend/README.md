# AERIS Backend

The `backend/` directory contains the FastAPI transport layer, domain models, deterministic airspace engine, scenario data and backend tests.

## Run

From the repository root:

```bash
python -m uvicorn backend.app.api.app:app --reload
```

Windows PowerShell:

```powershell
python -m uvicorn backend.app.api.app:app --reload
```

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

The current verified backend suite contains 286 passing tests.
