"""AERIS FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import health, airspace, decisions, copilot


def create_app() -> FastAPI:
    """Create and configure the AERIS FastAPI application."""
    app = FastAPI(
        title="AERIS — Airspace Emergency Response Intelligence System",
        description=(
            "Deterministic airspace intelligence API. "
            "The engine is authoritative; the API is an orchestration/transport layer. "
            "No safety-critical logic lives here."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Allow all origins in development; restrict in production via env config.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Read endpoints
    app.include_router(health.router, tags=["health"])
    app.include_router(airspace.router, tags=["airspace"])

    # Decision endpoints
    app.include_router(decisions.router, tags=["decisions"])

    # Copilot / AI orchestration endpoints
    app.include_router(copilot.router, tags=["copilot"])

    return app


app = create_app()
