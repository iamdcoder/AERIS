#!/usr/bin/env python3
"""Run the release-readiness checks for AERIS."""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.environ.copy()
ENV["PYTHONPATH"] = os.pathsep.join([os.path.join(ROOT, "backend"), ROOT])


def run(label: str, command: list[str]) -> None:
    print(f"\n=== {label} ===")
    result = subprocess.run(command, cwd=ROOT, env=ENV)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    run("Python compile check", [sys.executable, "-m", "compileall", "-q", "backend", "copilot", "scripts"])
    run("Full test suite", [sys.executable, "-m", "pytest", "-q"])
    run("Agentic flagship proof", [sys.executable, "scripts/run_agent_flagship.py"])
    print("\nAERIS release checks: PASS")
    print("Frontend release check: cd frontend; npm ci; npm run build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
