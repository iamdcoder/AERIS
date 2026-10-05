# AERIS Configuration

## 1. Environment file

Start from:

```text
.env.example
```

Create a local `.env` file and keep it out of version control.

---

## 2. Variables

### `GEMINI_API_KEY`

Gemini API credential used by the controlled Gemini investigation client.

Example:

```text
GEMINI_API_KEY=replace_me
```

Do not commit real credentials.

### `GEMINI_MODEL`

Gemini model identifier.

Current example:

```text
GEMINI_MODEL=gemini-2.5-flash
```

The Gemini client defaults to `gemini-2.5-flash` when no environment value is supplied.

### `AERIS_ENV`

General runtime environment label.

Current example:

```text
AERIS_ENV=development
```

### `BACKEND_HOST`

Backend host configuration value retained for local deployment conventions.

Current example:

```text
BACKEND_HOST=127.0.0.1
```

### `BACKEND_PORT`

Backend port convention.

Current example:

```text
BACKEND_PORT=8000
```

### `VITE_API_BASE_URL`

Base URL used by the React frontend for API calls.

Current local example:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### `VITE_OPERATIONS_WS_URL`

Optional explicit WebSocket URL for the live operational feed. In normal Vite development the browser derives `/ws/operations` from the current host, so this can remain empty.

Example for a separately deployed API server:

```text
VITE_OPERATIONS_WS_URL=wss://example-host.example/ws/operations
```

---

## 3. Gemini fallback behavior

Gemini is not required for the deterministic flagship proof.

The hybrid investigation path attempts Gemini and falls back to deterministic investigation when Gemini cannot be initialized or the investigation does not produce sufficient evidence.

Therefore the system has two operating modes:

```text
HYBRID
Gemini investigation + deterministic downstream pipeline

FALLBACK
Deterministic investigation + deterministic downstream pipeline
```

---

## 4. CORS

The FastAPI application currently allows all origins in development:

```text
allow_origins=["*"]
```

This is convenient for a local hackathon environment but should be restricted before any production deployment.

---

## 5. In-memory copilot runs

The current copilot API stores orchestrators in an in-memory `_RUNS` dictionary protected by a lock.

This means:

- it is appropriate for a local/demo process;
- restart loses stored runs;
- multiple backend processes would not share run state;
- persistent orchestration storage is not implemented.

---

## 6. Dependency installation

Python:

```bash
pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm ci
```

Vite is configured to read the root `.env` file, so the `VITE_*` values in `.env.example` are available to the frontend when you run Vite from `frontend/`.
