"""AERIS backend entry point.

From repository root:
    python -m uvicorn backend.app.api.app:app --host 127.0.0.1 --port 8000

For the hackathon demo, run a single Uvicorn process because Copilot run
state is intentionally in memory.
"""
from backend.app.api.app import app  # noqa: F401
