#!/usr/bin/env python3
"""AERIS submission preflight.

Runs the repository checks that can be verified locally and labels checks that
are blocked by missing external dependencies instead of claiming false success.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_check(name: str, command: list[str], *, cwd: Path = ROOT, timeout: int = 120) -> bool:
    print(f"[CHECK] {name}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("  [BLOCKED BY ENVIRONMENT] command timed out")
        return False

    if result.returncode == 0:
        print("  [PASS]")
        tail = result.stdout.strip().splitlines()[-3:]
        for line in tail:
            print(f"    {line}")
        return True

    print(f"  [FAIL] exit code {result.returncode}")
    tail = result.stdout.strip().splitlines()[-8:]
    for line in tail:
        print(f"    {line}")
    return False


def check_live_replay() -> bool:
    print("[CHECK] Operational replay")
    try:
        from backend.app.operations import get_replay_controller

        controller = get_replay_controller()
        controller.set_tick_seconds(0.05)
        controller.reset(stop_at_minute=35)
        snapshot = controller.step(35)
        if snapshot.last_simulation_time_min != 35 or not snapshot.done or snapshot.running:
            print(
                "  [FAIL] replay did not reach a stopped T+35 state"
            )
            return False
        print("  [PASS] deterministic operational timeline reached T+35")
        return True
    except Exception as exc:
        print(f"  [FAIL] {type(exc).__name__}: {exc}")
        return False


def check_api_smoke() -> bool:
    print("[CHECK] FastAPI health + operational WebSocket")
    try:
        from fastapi.testclient import TestClient
        from backend.app.api.app import create_app

        with TestClient(create_app()) as client:
            health = client.get("/health")
            live = client.get("/operations/live")
            if health.status_code != 200 or live.status_code != 200:
                print(
                    f"  [FAIL] health={health.status_code}, operations/live={live.status_code}"
                )
                return False
            with client.websocket_connect("/ws/operations") as socket:
                snapshot = socket.receive_json()
                if "version" not in snapshot and snapshot.get("type") != "heartbeat":
                    print("  [FAIL] WebSocket payload is missing version/heartbeat metadata")
                    return False
        print("  [PASS] /health=200, /operations/live=200, /ws/operations=connected")
        return True
    except Exception as exc:  # pragma: no cover - diagnostic path
        print(f"  [FAIL] {type(exc).__name__}: {exc}")
        return False


def check_docs() -> bool:
    print("[CHECK] Documentation consistency")
    files = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "PERSON1_README.md", ROOT / "backend" / "README.md", ROOT / "scripts" / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    forbidden = [
        "uploaded source snapshot does not currently expose a backend WebSocket route",
        "WebSocket support remains a documented future interface until the backend route is actually implemented",
        "The current uploaded backend source does not yet register a WebSocket route",
        "planned/contracted interface",
        "PYTHONPATH=backend python scripts/run_flagship.py",
        "PYTHONPATH=backend python scripts/run_agent_flagship.py",
        "PYTHONPATH=backend uvicorn app.api.app:app --reload",
    ]
    stale_count_patterns = [r"\b272 passed\b", r"\b121 passed\b", r"\b393 passed\b"]
    violations: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            if needle in text:
                violations.append(f"{path.relative_to(ROOT)} contains: {needle}")
        if path.name in {"README.md", "testing.md", "build-status.md"}:
            for pattern in stale_count_patterns:
                if re.search(pattern, text):
                    violations.append(f"{path.relative_to(ROOT)} contains stale count: {pattern}")
    if violations:
        print("  [FAIL]")
        for violation in violations:
            print(f"    {violation}")
        return False
    print("  [PASS] transport wording, commands, and historical test counts are consistent")
    return True


def check_security() -> bool:
    print("[CHECK] Submission hygiene")
    if (ROOT / ".env").exists():
        print("  [FAIL] .env is present in the submission tree")
        return False
    env_example = ROOT / ".env.example"
    if not env_example.exists():
        print("  [FAIL] .env.example is missing")
        return False

    suspicious = re.compile(r"AIza[0-9A-Za-z_-]{20,}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|(?:api[_-]?key|secret)\s*=\s*['\"][^'\"]+['\"]", re.I)
    ignored_dirs = {".git", "node_modules", "dist", "__pycache__", ".pytest_cache", ".venv"}
    hits = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in ignored_dirs for part in path.parts):
            continue
        if path.name in {".env.example", "package-lock.json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if suspicious.search(text):
            hits.append(str(path.relative_to(ROOT)))
    if hits:
        print("  [FAIL] suspicious credential material found:")
        for hit in hits[:20]:
            print(f"    {hit}")
        return False
    print("  [PASS] no .env file or obvious credential material found")
    return True


def main() -> int:
    print("========================================================")
    print(" AERIS SUBMISSION PREFLIGHT")
    print("========================================================")
    checks: list[tuple[str, bool, bool]] = []  # name, passed, blocked

    checks.append(("Python environment", sys.version_info >= (3, 10), False))
    if checks[-1][1]:
        print("[CHECK] Python environment")
        print(f"  [PASS] {sys.version.split()[0]}")
    else:
        print("[CHECK] Python environment\n  [FAIL]")

    checks.append(("compileall", run_check("Python compileall", [sys.executable, "-m", "compileall", "-q", "backend", "copilot", "scripts"]), False))
    checks.append(("Python tests", run_check("Backend + copilot tests", [sys.executable, "-m", "pytest", "backend/tests", "copilot/tests", "-q"], timeout=180), False))
    checks.append(("Flagship runner", run_check("Deterministic flagship", [sys.executable, "scripts/run_flagship.py"], timeout=120), False))
    checks.append(("Agent flagship", run_check("Agentic flagship", [sys.executable, "scripts/run_agent_flagship.py"], timeout=120), False))
    checks.append(("Live replay", check_live_replay(), False))
    checks.append(("API smoke", check_api_smoke(), False))
    checks.append(("Frontend regression test", run_check("Frontend node test", ["node", "--test", "src/lib/dashboardAdapter.test.js"], cwd=FRONTEND, timeout=30), False))

    vite = FRONTEND / "node_modules" / ".bin" / ("vite.cmd" if os.name == "nt" else "vite")
    if vite.exists():
        checks.append(("Frontend build", run_check("Frontend production build", ["npm", "run", "build"], cwd=FRONTEND, timeout=120), False))
    else:
        print("[CHECK] Frontend production build\n  [BLOCKED BY ENVIRONMENT] frontend dependencies are not installed")
        checks.append(("Frontend build", False, True))

    checks.append(("Documentation", check_docs(), False))
    checks.append(("Security", check_security(), False))

    failed = [name for name, passed, blocked in checks if not passed and not blocked]
    blocked = [name for name, passed, is_blocked in checks if is_blocked]

    print("\n========================================================")
    if failed:
        print("AERIS SUBMISSION STATUS: NOT READY")
        print("Failed checks:")
        for name in failed:
            print(f"  - {name}")
        if blocked:
            print("Blocked by environment:")
            for name in blocked:
                print(f"  - {name}")
        return 1

    if blocked:
        print("AERIS SUBMISSION STATUS: BLOCKED BY ENVIRONMENT")
        print("Checks that still require local dependency access:")
        for name in blocked:
            print(f"  - {name}")
        print("Run `cd frontend && npm ci && npm run build`, then rerun this preflight.")
        return 2

    print("AERIS SUBMISSION STATUS: JUDGE READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
