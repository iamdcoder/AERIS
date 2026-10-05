"""AERIS backend entry point.

Run from repository root:
    Linux/macOS:
        python -m uvicorn backend.app.api.app:app --host 127.0.0.1 --port 8000
    Windows (PowerShell / CMD):
        python -m uvicorn backend.app.api.app:app --host 127.0.0.1 --port 8000

Or directly run this script:
    python backend/main.py
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.app import app  # noqa: F401 — re-export for uvicorn

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api.app:app", host="127.0.0.1", port=8000, reload=False)

