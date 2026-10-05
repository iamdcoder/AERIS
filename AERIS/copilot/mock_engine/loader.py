"""JSON fixture loader for the test-only MockEngineClient."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FixtureError(RuntimeError):
    """Raised when a mock fixture is missing or malformed."""


def load_fixture(name: str) -> dict[str, Any]:
    path = Path(__file__).with_name(name)
    try:
        with path.open(encoding="utf-8") as fixture_file:
            value = json.load(fixture_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureError(f"Unable to load mock fixture {name!r}: {exc}") from exc
    if not isinstance(value, dict):
        raise FixtureError(f"Mock fixture {name!r} must contain a JSON object")
    return value
