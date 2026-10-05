#!/usr/bin/env python3
"""Watch the simulated AERIS operational feed advance in real time.

Run from repository root:
    python scripts/run_live_replay.py

Optional:
    python scripts/run_live_replay.py --stop-at 35
"""
from __future__ import annotations

import argparse
import os
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.app.operations import get_replay_controller


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay AERIS operational events.")
    parser.add_argument("--stop-at", type=int, default=35, choices=range(1, 36))
    args = parser.parse_args()

    controller = get_replay_controller()
    controller.reset(stop_at_minute=args.stop_at)
    controller.start(reset_first=False, stop_at_minute=args.stop_at)

    printed_sequence = -1
    try:
        while True:
            snapshot = controller.snapshot()
            latest = snapshot.recent_events[0] if snapshot.recent_events else None
            if latest and latest.sequence != printed_sequence:
                printed_sequence = latest.sequence
                print(
                    f"T+{latest.simulation_time_min or 0:02d} | "
                    f"{latest.event_type.value:<24} "
                    f"{latest.entity_type}:{latest.entity_id}"
                )

            if snapshot.done and not snapshot.running:
                break
            time.sleep(0.15)
    finally:
        controller.stop()

    print(
        f"\nLIVE REPLAY COMPLETE — operational timeline reached T+{args.stop_at:02d}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
