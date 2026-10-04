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


def assess_investigation_quality(
    *,
    tool_names: list[str],
    world_state: dict,
) -> InvestigationQuality:
    completed = set(
        tool_names
    )

    required = [
        "get_airspace_state",
        "get_disruptions",
        "get_target_flight",
    ]

    alerts = world_state.get(
        "alerts",
        []
    )

    network_summary = (
        world_state.get(
            "network_summary",
            {}
        )
    )

    has_weather_signal = (
        bool(
            world_state.get(
                "weather_cells",
                []
            )
        )
        or any(
            alert.get("type")
            == "WEATHER_EXPANSION"
            for alert in alerts
        )
    )

    has_airport_signal = (
        bool(
            world_state.get(
                "airports",
                []
            )
        )
        and any(
            airport.get(
                "operational_status"
            )
            != "NORMAL"
            for airport
            in world_state.get(
                "airports",
                []
            )
        )
    )

    has_sector_signal = (
        bool(
            world_state.get(
                "sectors",
                []
            )
        )
        and any(
            sector.get(
                "status"
            )
            == "STRESSED"
            for sector
            in world_state.get(
                "sectors",
                []
            )
        )
    )

    has_network_signal = (
        int(
            network_summary.get(
                "aircraft_in_holding",
                0,
            )
        )
        > 0
        or int(
            network_summary.get(
                "stressed_sectors",
                0,
            )
        )
        > 0
    )

    conditional_requirements = []

    if has_weather_signal:
        conditional_requirements.append(
            "get_weather_state"
        )

    if has_airport_signal:
        conditional_requirements.append(
            "get_airport_state"
        )

    if has_sector_signal:
        conditional_requirements.append(
            "get_sector_state"
        )

    if has_network_signal:
        conditional_requirements.append(
            "get_network_metrics"
        )

    required.extend(
        conditional_requirements
    )

    completed_checks = [
        name
        for name
        in required
        if name in completed
    ]

    missing_checks = [
        name
        for name
        in required
        if name not in completed
    ]

    score = (
        len(completed_checks)
        / len(required)
        if required
        else 1.0
    )

    reasons = []

    if missing_checks:
        reasons.append(
            (
                "Investigation is missing required "
                "evidence for the current operational signals."
            )
        )

    if not world_state:
        reasons.append(
            "Current world state is unavailable."
        )

    if (
        "get_target_flight"
        in completed
        and "get_disruptions"
        in completed
    ):
        reasons.append(
            (
                "Target-flight and disruption evidence "
                "have been collected."
            )
        )

    sufficient = (
        not missing_checks
        and bool(world_state)
        and score >= 0.80
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