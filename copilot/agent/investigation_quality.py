from __future__ import annotations

from typing import Any


class InvestigationQuality:
    def __init__(
        self,
        *,
        sufficient: bool,
        score: float,
        completed_checks: list[str] | None = None,
        missing_checks: list[str] | None = None,
        reasons: list[str] | None = None,
    ) -> None:
        self.sufficient = sufficient
        self.score = score
        self.completed_checks = completed_checks or []
        self.missing_checks = missing_checks or []
        self.reasons = reasons or []

    def model_dump(self) -> dict[str, Any]:
        return {
            "sufficient": self.sufficient,
            "score": self.score,
            "completed_checks": self.completed_checks,
            "missing_checks": self.missing_checks,
            "reasons": self.reasons,
        }


def _has_target_state(
    world_state: dict[str, Any],
) -> bool:
    if world_state.get("target_flight"):
        return True

    target = world_state.get("target")

    if isinstance(target, dict):
        if target.get("flight"):
            return True

        if target.get("id"):
            return True

    aircraft = world_state.get("aircraft")

    return bool(aircraft)


def _has_airspace_snapshot(
    world_state: dict[str, Any],
) -> bool:
    return bool(
        world_state.get("aircraft")
        or world_state.get("sectors")
        or world_state.get("airports")
        or world_state.get("weather_cells")
    )


def _has_disruption_state(
    world_state: dict[str, Any],
) -> bool:
    if world_state.get("alerts"):
        return True

    disruptions = world_state.get(
        "disruptions",
        {},
    )

    if isinstance(disruptions, dict):
        return bool(
            disruptions.get("disruptions")
            or disruptions.get("weather_cells")
            or disruptions.get("restrictions")
        )

    return bool(disruptions)


def _has_weather_signal(
    world_state: dict[str, Any],
) -> bool:
    weather_cells = world_state.get(
        "weather_cells",
        [],
    )

    if weather_cells:
        return True

    alerts = world_state.get(
        "alerts",
        [],
    )

    return any(
        isinstance(alert, dict)
        and alert.get("type")
        == "WEATHER_EXPANSION"
        for alert in alerts
    )


def _has_airport_signal(
    world_state: dict[str, Any],
) -> bool:
    airports = world_state.get(
        "airports",
        [],
    )

    return any(
        isinstance(airport, dict)
        and str(
            airport.get(
                "operational_status",
                "",
            )
        ).upper()
        not in {
            "",
            "NORMAL",
            "OPERATIONAL",
        }
        for airport in airports
    )


def _has_sector_signal(
    world_state: dict[str, Any],
) -> bool:
    sectors = world_state.get(
        "sectors",
        [],
    )

    for sector in sectors:
        if not isinstance(sector, dict):
            continue

        status = str(
            sector.get(
                "status",
                "",
            )
        ).upper()

        if status in {
            "STRESSED",
            "CONGESTED",
            "OVERLOADED",
            "CRITICAL",
        }:
            return True

        utilization = sector.get(
            "projected_utilization"
        )

        if utilization is None:
            utilization = sector.get(
                "utilization_pct"
            )

        try:
            if float(utilization) >= 85:
                return True
        except (
            TypeError,
            ValueError,
        ):
            pass

    return False


def _has_network_signal(
    world_state: dict[str, Any],
) -> bool:
    summary = world_state.get(
        "network_summary",
        {},
    )

    if not isinstance(summary, dict):
        return False

    try:
        holding = int(
            summary.get(
                "aircraft_in_holding",
                0,
            )
            or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        holding = 0

    try:
        stressed = int(
            summary.get(
                "stressed_sectors",
                0,
            )
            or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        stressed = 0

    return holding > 0 or stressed > 0


def assess_investigation_quality(
    *,
    tool_names: list[str],
    world_state: dict[str, Any],
) -> InvestigationQuality:
    """
    Assess whether the investigation has enough evidence to continue.

    Important hybrid behavior:

    The deterministic OBSERVE phase may already have supplied the
    complete baseline snapshot to Gemini. Gemini therefore does not
    need to repeat every baseline read tool just to satisfy this gate.

    The model must still make at least one successful investigation
    tool call so that the hybrid path represents an actual investigation
    rather than a plain pass-through.
    """

    completed = set(tool_names)

    baseline_state_available = (
        _has_airspace_snapshot(world_state)
    )

    target_state_available = (
        _has_target_state(world_state)
    )

    disruption_state_available = (
        _has_disruption_state(world_state)
    )

    baseline_completed = []

    if (
        "get_airspace_state" in completed
        or baseline_state_available
    ):
        baseline_completed.append(
            "get_airspace_state"
        )

    if (
        "get_disruptions" in completed
        or disruption_state_available
    ):
        baseline_completed.append(
            "get_disruptions"
        )

    if (
        "get_target_flight" in completed
        or target_state_available
    ):
        baseline_completed.append(
            "get_target_flight"
        )

    missing_checks = []

    if "get_airspace_state" not in baseline_completed:
        missing_checks.append(
            "get_airspace_state"
        )

    if "get_disruptions" not in baseline_completed:
        missing_checks.append(
            "get_disruptions"
        )

    if "get_target_flight" not in baseline_completed:
        missing_checks.append(
            "get_target_flight"
        )

    conditional_requirements = []

    if _has_weather_signal(world_state):
        conditional_requirements.append(
            (
                "get_weather_state",
                bool(
                    world_state.get(
                        "weather_cells"
                    )
                )
                or "get_weather_state"
                in completed,
            )
        )

    if _has_airport_signal(world_state):
        conditional_requirements.append(
            (
                "get_airport_state",
                bool(
                    world_state.get(
                        "airports"
                    )
                )
                and "get_airport_state"
                in completed,
            )
        )

    if _has_sector_signal(world_state):
        conditional_requirements.append(
            (
                "get_sector_state",
                bool(
                    world_state.get(
                        "sectors"
                    )
                )
                or "get_sector_state"
                in completed,
            )
        )

    if _has_network_signal(world_state):
        conditional_requirements.append(
            (
                "get_network_metrics",
                bool(
                    world_state.get(
                        "network_summary"
                    )
                )
                or "get_network_metrics"
                in completed,
            )
        )

    for name, satisfied in conditional_requirements:
        if satisfied:
            baseline_completed.append(name)
        else:
            missing_checks.append(name)

    # Duplicate-safe ordering.
    completed_checks = list(
        dict.fromkeys(
            baseline_completed
            + [
                name
                for name in completed
                if name
                in {
                    "get_airspace_state",
                    "get_disruptions",
                    "get_target_flight",
                    "get_weather_state",
                    "get_airport_state",
                    "get_sector_state",
                    "get_network_metrics",
                }
            ]
        )
    )

    missing_checks = list(
        dict.fromkeys(
            missing_checks
        )
    )

    score = (
        len(completed_checks)
        / (
            len(completed_checks)
            + len(missing_checks)
        )
        if (
            completed_checks
            or missing_checks
        )
        else 0.0
    )

    successful_investigation_call = any(
        name
        in {
            "get_airspace_state",
            "get_disruptions",
            "get_target_flight",
            "get_weather_state",
            "get_airport_state",
            "get_sector_state",
            "get_network_metrics",
        }
        for name in completed
    )

    reasons = []

    if baseline_state_available:
        reasons.append(
            "Deterministic observation already supplied "
            "the baseline airspace snapshot."
        )
    else:
        reasons.append(
            "The baseline airspace snapshot is unavailable."
        )

    if successful_investigation_call:
        reasons.append(
            "Gemini successfully gathered additional "
            "investigation evidence."
        )
    else:
        reasons.append(
            "No successful investigation tool call was recorded."
        )

    if missing_checks:
        reasons.append(
            "Investigation is missing evidence required "
            "for the available operational signals."
        )

    sufficient = (
        baseline_state_available
        and target_state_available
        and disruption_state_available
        and successful_investigation_call
        and not missing_checks
        and bool(world_state)
    )

    if sufficient:
        score = 1.0

        reasons.append(
            "Investigation has sufficient evidence "
            "to proceed to intervention planning."
        )

    return InvestigationQuality(
        sufficient=sufficient,
        score=score,
        completed_checks=completed_checks,
        missing_checks=missing_checks,
        reasons=reasons,
    )