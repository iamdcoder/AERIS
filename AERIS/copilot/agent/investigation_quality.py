from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InvestigationQuality(BaseModel):
    sufficient: bool

    score: float

    completed_checks: list[str] = Field(
        default_factory=list
    )

    missing_checks: list[str] = Field(
        default_factory=list
    )

    reasons: list[str] = Field(
        default_factory=list
    )


def _has_target_flight(
    world_state: dict[str, Any],
) -> bool:
    target_flight = world_state.get(
        "target_flight"
    )

    if (
        isinstance(
            target_flight,
            dict,
        )
        and target_flight.get("id")
    ):
        return True

    target = world_state.get(
        "target"
    )

    if isinstance(
        target,
        dict,
    ):
        if target.get("id"):
            return True

        if target.get("flight"):
            return True

    return False


def _has_airspace_snapshot(
    world_state: dict[str, Any],
) -> bool:
    return bool(
        world_state.get("aircraft")
        or world_state.get("sectors")
        or world_state.get("airports")
        or world_state.get("weather_cells")
        or world_state.get("target_flight")
    )


def _has_disruption_state(
    world_state: dict[str, Any],
) -> bool:
    alerts = world_state.get(
        "alerts",
        [],
    )

    if alerts:
        return True

    disruptions = world_state.get(
        "disruptions"
    )

    return bool(disruptions)


def _weather_severity(
    world_state: dict[str, Any],
) -> str:
    highest = "NONE"

    ranking = {
        "NONE": 0,
        "LOW": 1,
        "MEDIUM": 2,
        "MODERATE": 2,
        "HIGH": 3,
        "SEVERE": 4,
        "CRITICAL": 5,
    }

    for cell in world_state.get(
        "weather_cells",
        [],
    ):
        if not isinstance(
            cell,
            dict,
        ):
            continue

        severity = str(
            cell.get(
                "severity",
                cell.get(
                    "intensity",
                    "NONE",
                ),
            )
        ).upper()

        if ranking.get(
            severity,
            0,
        ) > ranking.get(
            highest,
            0,
        ):
            highest = severity

    for alert in world_state.get(
        "alerts",
        [],
    ):
        if not isinstance(
            alert,
            dict,
        ):
            continue

        if str(
            alert.get(
                "type",
                "",
            )
        ).upper() != "WEATHER_EXPANSION":
            continue

        severity = str(
            alert.get(
                "severity",
                "HIGH",
            )
        ).upper()

        if ranking.get(
            severity,
            0,
        ) > ranking.get(
            highest,
            0,
        ):
            highest = severity

    return highest


def _has_weather_signal(
    world_state: dict[str, Any],
) -> bool:
    return (
        _weather_severity(
            world_state
        )
        != "NONE"
    )


def _has_airport_signal(
    world_state: dict[str, Any],
) -> bool:
    airports = world_state.get(
        "airports",
        [],
    )

    for airport in airports:
        if not isinstance(
            airport,
            dict,
        ):
            continue

        status = str(
            airport.get(
                "operational_status",
                "",
            )
        ).upper()

        if status not in {
            "",
            "NORMAL",
            "OPERATIONAL",
        }:
            return True

    return False


def _has_sector_signal(
    world_state: dict[str, Any],
) -> bool:
    sectors = world_state.get(
        "sectors",
        [],
    )

    for sector in sectors:
        if not isinstance(
            sector,
            dict,
        ):
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

        value = sector.get(
            "projected_utilization"
        )

        if value is None:
            value = sector.get(
                "utilization_pct"
            )

        try:
            numeric = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if numeric <= 2:
            numeric *= 100

        if numeric >= 85:
            return True

    return False


def _has_network_signal(
    world_state: dict[str, Any],
) -> bool:
    summary = world_state.get(
        "network_summary",
        {},
    )

    if not isinstance(
        summary,
        dict,
    ):
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

    return (
        holding > 0
        or stressed > 0
    )


def _primary_investigation_tool(
    world_state: dict[str, Any],
) -> str | None:
    """
    Determine the most important currently active investigation signal.

    Priority intentionally follows operational urgency:

        severe weather
            >
        degraded airport
            >
        stressed sector
            >
        network pressure

    This does not calculate aviation quantities. It only determines
    which existing evidence signal should be investigated first.
    """

    weather = _weather_severity(
        world_state
    )

    if weather in {
        "SEVERE",
        "CRITICAL",
        "HIGH",
    }:
        return "get_weather_state"

    if _has_airport_signal(
        world_state
    ):
        return "get_airport_state"

    if _has_sector_signal(
        world_state
    ):
        return "get_sector_state"

    if _has_network_signal(
        world_state
    ):
        return "get_network_metrics"

    if _has_weather_signal(
        world_state
    ):
        return "get_weather_state"

    return None


def assess_investigation_quality(
    *,
    tool_names: list[str],
    world_state: dict[str, Any],
) -> InvestigationQuality:
    """
    Assess whether Gemini gathered enough evidence to continue.

    The deterministic snapshot can establish the baseline context.

    Gemini must additionally investigate the most important currently
    active operational signal. This prevents a model from calling an
    arbitrary allowed tool and being marked sufficient.
    """

    completed = {
        str(
            name
        )
        for name in tool_names
    }

    completed_checks: list[str] = []
    missing_checks: list[str] = []
    reasons: list[str] = []

    baseline_requirements = [
        "get_airspace_state",
        "get_disruptions",
        "get_target_flight",
    ]

    baseline_available = (
        _has_airspace_snapshot(
            world_state
        )
        and _has_disruption_state(
            world_state
        )
        and _has_target_flight(
            world_state
        )
    )

    if baseline_available:
        completed_checks.extend(
            baseline_requirements
        )
    else:
        if not _has_airspace_snapshot(
            world_state
        ):
            missing_checks.append(
                "get_airspace_state"
            )

        if not _has_disruption_state(
            world_state
        ):
            missing_checks.append(
                "get_disruptions"
            )

        if not _has_target_flight(
            world_state
        ):
            missing_checks.append(
                "get_target_flight"
            )

    primary_tool = (
        _primary_investigation_tool(
            world_state
        )
    )

    if primary_tool is not None:
        if primary_tool in completed:
            completed_checks.append(
                primary_tool
            )
        else:
            missing_checks.append(
                primary_tool
            )

    secondary_tools = []

    if (
        _has_weather_signal(
            world_state
        )
        and primary_tool
        != "get_weather_state"
    ):
        secondary_tools.append(
            "get_weather_state"
        )

    if (
        _has_airport_signal(
            world_state
        )
        and primary_tool
        != "get_airport_state"
    ):
        secondary_tools.append(
            "get_airport_state"
        )

    if (
        _has_sector_signal(
            world_state
        )
        and primary_tool
        != "get_sector_state"
    ):
        secondary_tools.append(
            "get_sector_state"
        )

    if (
        _has_network_signal(
            world_state
        )
        and primary_tool
        != "get_network_metrics"
    ):
        secondary_tools.append(
            "get_network_metrics"
        )

    completed_checks.extend(
        tool
        for tool in secondary_tools
        if tool in completed
    )

    completed_checks = list(
        dict.fromkeys(
            completed_checks
        )
    )

    missing_checks = list(
        dict.fromkeys(
            missing_checks
        )
    )

    investigation_safe_tools = {
        "get_airspace_state",
        "get_disruptions",
        "get_target_flight",
        "get_sector_state",
        "get_airport_state",
        "get_weather_state",
        "get_restrictions",
        "get_network_metrics",
    }

    successful_investigation_call = any(
        tool in investigation_safe_tools
        for tool in completed
    )

    if baseline_available:
        reasons.append(
            (
                "The deterministic observation snapshot supplied "
                "the baseline airspace, target-flight and disruption state."
            )
        )
    else:
        reasons.append(
            (
                "The deterministic observation snapshot is incomplete."
            )
        )

    if primary_tool is not None:
        if primary_tool in completed:
            reasons.append(
                (
                    f"Gemini investigated the primary operational "
                    f"signal using {primary_tool}."
                )
            )
        else:
            reasons.append(
                (
                    f"The primary operational signal requires "
                    f"{primary_tool} investigation."
                )
            )
    else:
        reasons.append(
            (
                "No material primary investigation signal "
                "was detected in the supplied world state."
            )
        )

    if successful_investigation_call:
        reasons.append(
            (
                "At least one investigation-safe tool call "
                "completed successfully."
            )
        )
    else:
        reasons.append(
            (
                "No investigation-safe tool call completed successfully."
            )
        )

    sufficient = (
        bool(world_state)
        and baseline_available
        and successful_investigation_call
        and (
            primary_tool is None
            or primary_tool in completed
        )
        and not (
            {
                "get_airspace_state",
                "get_disruptions",
                "get_target_flight",
            }
            - set(completed_checks)
        )
    )

    if sufficient:
        score = 1.0
    else:
        required_for_gate = 4 if primary_tool else 3

        score = min(
            1.0,
            len(
                completed_checks
            )
            / required_for_gate,
        )

    if missing_checks:
        reasons.append(
            (
                "Investigation remains incomplete for: "
                + ", ".join(
                    missing_checks
                )
            )
        )

    if sufficient:
        reasons.append(
            (
                "Investigation has sufficient evidence "
                "to proceed to intervention planning."
            )
        )

    return InvestigationQuality(
        sufficient=sufficient,
        score=score,
        completed_checks=completed_checks,
        missing_checks=missing_checks,
        reasons=reasons,
    )