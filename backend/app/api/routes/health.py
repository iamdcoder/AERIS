"""Health check endpoint."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Service health check")
def health():
    """Return the service liveness status."""
    return {"status": "ok", "service": "aeris"}
