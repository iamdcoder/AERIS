from typing import Any

from .state import (
    InvestigationPlan,
    InvestigationPriority,
    InvestigationQuestion,
)


def _find_degraded_airports(
    world_state: dict[str, Any],
) -> list[str]:
    airports = world_state.get(
        "airports",
        [],
    )

    return [
        str(
            airport.get("id")
        )
        for airport in airports
        if airport.get(
            "operational_status"
        ) != "NORMAL"
    ]


def _find_stressed_sectors(
    world_state: dict[str, Any],
) -> list[str]:
    sectors = world_state.get(
        "sectors",
        [],
    )

    return [
        str(
            sector.get("id")
        )
        for sector in sectors
        if sector.get(
            "status"
        ) == "STRESSED"
    ]


def _has_alert_type(
    alerts: list[dict[str, Any]],
    alert_type: str,
) -> bool:
    return any(
        alert.get("type")
        == alert_type
        for alert in alerts
    )


def build_investigation_plan(
    world_state: dict[str, Any],
) -> InvestigationPlan:
    disruptions = world_state.get(
        "disruptions",
        {},
    )

    alerts = disruptions.get(
        "disruptions",
        [],
    )

    questions: list[
        InvestigationQuestion
    ] = []

    question_number = 1

    def add_question(
        *,
        question: str,
        rationale: str,
        tool_name: str,
        arguments: dict[str, Any],
        priority: InvestigationPriority,
    ) -> None:
        nonlocal question_number

        questions.append(
            InvestigationQuestion(
                question_id=(
                    f"INV-{question_number:02d}"
                ),
                question=question,
                rationale=rationale,
                tool_name=tool_name,
                arguments=arguments,
                priority=priority,
            )
        )

        question_number += 1

    stressed_sectors = (
        _find_stressed_sectors(
            world_state
        )
    )

    degraded_airports = (
        _find_degraded_airports(
            world_state
        )
    )

    has_weather = (
        _has_alert_type(
            alerts,
            "WEATHER_EXPANSION",
        )
        or bool(
            world_state.get(
                "weather_cells",
                [],
            )
        )
    )

    has_capacity_degradation = (
        _has_alert_type(
            alerts,
            "AIRPORT_CAPACITY_DEGRADATION",
        )
        or bool(degraded_airports)
    )

    has_sector_congestion = (
        _has_alert_type(
            alerts,
            "SECTOR_CONGESTION",
        )
        or bool(stressed_sectors)
    )

    has_restriction_signal = (
        _has_alert_type(
            alerts,
            "AIRSPACE_RESTRICTION",
        )
        or bool(
            world_state.get(
                "restrictions",
                [],
            )
        )
    )

    if has_weather:
        add_question(
            question=(
                "What weather cells or forecast changes "
                "are threatening the target's operational corridor?"
            ),
            rationale=(
                "Weather may be the primary trigger or may "
                "be interacting with airport and sector capacity."
            ),
            tool_name="get_weather_state",
            arguments={},
            priority=InvestigationPriority.CRITICAL,
        )

    if has_capacity_degradation:
        for airport_id in degraded_airports:
            add_question(
                question=(
                    f"What is the current capacity and "
                    f"operational status of airport {airport_id}?"
                ),
                rationale=(
                    "Reduced arrival/departure capacity can "
                    "increase holding and change intervention feasibility."
                ),
                tool_name="get_airport_state",
                arguments={
                    "airport_id": airport_id
                },
                priority=InvestigationPriority.CRITICAL,
            )

    if has_sector_congestion:
        for sector_id in stressed_sectors:
            add_question(
                question=(
                    f"How close is sector {sector_id} "
                    "to its effective capacity?"
                ),
                rationale=(
                    "A locally attractive intervention may "
                    "push additional demand into an already stressed sector."
                ),
                tool_name="get_sector_state",
                arguments={
                    "sector_id": sector_id
                },
                priority=InvestigationPriority.CRITICAL,
            )

    if has_restriction_signal:
        add_question(
            question=(
                "Are there active airspace restrictions "
                "that should influence intervention generation?"
            ),
            rationale=(
                "Restrictions can invalidate otherwise attractive "
                "candidate interventions."
            ),
            tool_name="get_restrictions",
            arguments={},
            priority=InvestigationPriority.HIGH,
        )

    network_summary = world_state.get(
        "network_summary",
        {},
    )

    if (
        int(
            network_summary.get(
                "aircraft_in_holding",
                0,
            )
        )
        > 0
        or stressed_sectors
    ):
        add_question(
            question=(
                "What is the current network-level pressure "
                "outside the target flight?"
            ),
            rationale=(
                "The decision should account for surrounding "
                "traffic and not isolate F102."
            ),
            tool_name="get_network_metrics",
            arguments={},
            priority=InvestigationPriority.HIGH,
        )

    # Keep the investigation set compact.
    # The agent will later be able to dynamically prioritize
    # and stop when enough evidence has been collected.
    questions = sorted(
        questions,
        key=lambda item: (
            list(
                InvestigationPriority
            ).index(
                item.priority
            ),
            item.question_id,
        ),
    )

    objective = (
        "Determine why the target flight is degrading, "
        "which resources are constraining it, and what evidence "
        "must be considered before intervention generation."
    )

    rationale = (
        "Prioritize causal evidence before generating "
        "interventions so AERIS does not react to a symptom "
        "without understanding the network condition."
    )

    return InvestigationPlan(
        objective=objective,
        questions=questions,
        rationale=rationale,
    )


def update_plan_completeness(
    plan: InvestigationPlan,
) -> InvestigationPlan:
    if not plan.questions:
        plan.completeness = 1.0
        return plan

    completed = sum(
        question.status
        == "COMPLETED"
        for question in plan.questions
    )

    plan.completeness = (
        completed / len(plan.questions)
    )

    return plan