"""
Shared fixtures for engine tests.

Ensures the public engine singleton is reset to a deterministic baseline
before and after every test in this package, preventing cross-module
state pollution when tests run in random order.
"""
import pytest

from app.engine import public


@pytest.fixture(autouse=True)
def _reset_public_engine():
    """Reset the public engine registry before and after every engine test."""
    public.reset_engine()
    yield
    public.reset_engine()
