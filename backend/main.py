"""AERIS backend entry point.

Run with:
    PYTHONPATH=backend uvicorn main:app --reload --app-dir backend
or simply:
    PYTHONPATH=backend .venv/bin/uvicorn app.api.app:app --reload
"""
from app.api.app import app  # noqa: F401 — re-export for uvicorn
