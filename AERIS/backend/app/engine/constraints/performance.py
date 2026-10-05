from __future__ import annotations

from typing import Any

DEFAULT_MAX_ALTITUDE_FT = 39000.0
DEGRADED_MAX_ALTITUDE_FT = 33000.0
DEFAULT_MAX_SPEED_KT = 460.0


def performance_check(
    state: Any,
    flight: Any,
    cruise_altitude_ft: float,
    speed_kt: float,
) -> dict[str, Any]:
    """Validate candidate cruise altitude and speed against aircraft performance envelope."""
    altitude = float(cruise_altitude_ft)
    speed = float(speed_kt)

    # Degraded status constrains maximum permitted operational altitude.
    if flight.status == "DEGRADED":
        max_altitude = float(getattr(flight, "degraded_max_altitude_ft", DEGRADED_MAX_ALTITUDE_FT))
    else:
        max_altitude = float(getattr(flight, "max_altitude_ft", DEFAULT_MAX_ALTITUDE_FT))

    max_speed = float(getattr(flight, "max_speed_kt", DEFAULT_MAX_SPEED_KT))

    alt_passed = altitude <= max_altitude
    speed_passed = speed <= max_speed
    passed = alt_passed and speed_passed

    rejection_reasons = []
    if not alt_passed:
        rejection_reasons.append(
            f"Candidate cruise altitude {altitude:.0f} ft exceeds maximum performance envelope "
            f"({max_altitude:.0f} ft) for aircraft status {flight.status}"
        )
    if not speed_passed:
        rejection_reasons.append(
            f"Candidate speed {speed:.0f} kt exceeds maximum performance speed ({max_speed:.0f} kt)"
        )

    return {
        "passed": passed,
        "max_altitude_ft": max_altitude,
        "max_speed_kt": max_speed,
        "altitude_passed": alt_passed,
        "speed_passed": speed_passed,
        "violation_reason": rejection_reasons[0] if rejection_reasons else None,
        "rejection_reasons": rejection_reasons,
    }
