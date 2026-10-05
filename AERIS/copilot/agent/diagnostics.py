from typing import Any

from .state import (
    CausalEdge,
    CausalGraph,
    CausalNode,
    Diagnosis,
)


def _tool_data(
    investigation_results: list[dict[str, Any]],
    tool_name: str,
) -> list[dict[str, Any]]:
    return [
        result
        for result in investigation_results
        if result.get(
            "tool_name"
        ) == tool_name
    ]


def build_causal_diagnosis(
    *,
    world_state: dict[str, Any],
    investigation_results: list[dict[str, Any]],
    target_flight_id: str,
    evidence_ids: list[str],
    evidence_completeness: float,
) -> Diagnosis:
    disruptions = world_state.get(
        "disruptions",
        {},
    )

    alerts = disruptions.get(
        "disruptions",
        [],
    )

    target_data = world_state.get(
        "target",
        {},
    ).get(
        "flight",
        {},
    )

    weather_results = _tool_data(
        investigation_results,
        "get_weather_state",
    )

    airport_results = _tool_data(
        investigation_results,
        "get_airport_state",
    )

    sector_results = _tool_data(
        investigation_results,
        "get_sector_state",
    )

    network_results = _tool_data(
        investigation_results,
        "get_network_metrics",
    )

    graph = CausalGraph()

    graph.nodes.append(
        CausalNode(
            node_id="target_flight",
            node_type="FLIGHT",
            label=(
                f"Target flight {target_flight_id}"
            ),
            evidence_ids=evidence_ids,
        )
    )

    severe_weather = any(
        item.get(
            "severity"
        ) in {
            "HIGH",
            "SEVERE",
        }
        for result in weather_results
        for item in result.get(
            "data",
            {},
        ).get(
            "weather_cells",
            [],
        )
    )

    degraded_airports = [
        result.get(
            "data",
            {},
        ).get(
            "airport",
            {},
        )
        for result in airport_results
    ]

    stressed_sectors = [
        result.get(
            "data",
            {},
        ).get(
            "sector",
            {},
        )
        for result in sector_results
    ]

    if weather_results:
        graph.nodes.append(
            CausalNode(
                node_id="weather",
                node_type="WEATHER",
                label="Convective weather",
                evidence_ids=evidence_ids,
            )
        )

    for airport in degraded_airports:
        airport_id = str(
            airport.get(
                "id",
                "UNKNOWN",
            )
        )

        node_id = (
            f"airport_{airport_id}"
        )

        graph.nodes.append(
            CausalNode(
                node_id=node_id,
                node_type="AIRPORT",
                label=(
                    f"Airport {airport_id} "
                    "capacity state"
                ),
                evidence_ids=evidence_ids,
            )
        )

        graph.edges.append(
            CausalEdge(
                source=node_id,
                target="target_flight",
                relationship=(
                    "degrades_destination_capacity_for"
                ),
                evidence_ids=evidence_ids,
            )
        )

        if weather_results:
            graph.edges.append(
                CausalEdge(
                    source="weather",
                    target=node_id,
                    relationship=(
                        "contributes_to_capacity_degradation"
                    ),
                    evidence_ids=evidence_ids,
                )
            )

    if stressed_sectors:
        graph.nodes.append(
            CausalNode(
                node_id="holding_pressure",
                node_type="NETWORK",
                label=(
                    "Holding / deviation pressure"
                ),
                evidence_ids=evidence_ids,
            )
        )

        for sector in stressed_sectors:
            sector_id = str(
                sector.get(
                    "id",
                    "UNKNOWN",
                )
            )

            node_id = (
                f"sector_{sector_id}"
            )

            graph.nodes.append(
                CausalNode(
                    node_id=node_id,
                    node_type="SECTOR",
                    label=(
                        f"Sector {sector_id} "
                        "capacity"
                    ),
                    evidence_ids=evidence_ids,
                )
            )

            graph.edges.append(
                CausalEdge(
                    source="holding_pressure",
                    target=node_id,
                    relationship=(
                        "increases_demand_pressure"
                    ),
                    evidence_ids=evidence_ids,
                )
            )

    if stressed_sectors and target_data:
        graph.edges.append(
            CausalEdge(
                source="target_flight",
                target="holding_pressure",
                relationship=(
                    "may_contribute_to_holding_pressure"
                ),
                evidence_ids=evidence_ids,
            )
        )

    primary_cause = (
        str(
            alerts[0].get(
                "type",
                "UNKNOWN_DEGRADATION",
            )
        )
        if alerts
        else "UNKNOWN_DEGRADATION"
    )

    secondary_causes = [
        str(
            alert.get(
                "type",
                "UNKNOWN",
            )
        )
        for alert in alerts[1:]
    ]

    affected_sectors = [
        str(
            sector.get(
                "id",
            )
        )
        for sector in stressed_sectors
        if sector.get("id") is not None
    ]

    affected_airports = [
        str(
            airport.get(
                "id",
            )
        )
        for airport in degraded_airports
        if airport.get("id") is not None
    ]

    causal_chain: list[str] = []

    if severe_weather:
        causal_chain.append(
            "Convective weather is affecting the operational environment."
        )

    if degraded_airports:
        causal_chain.append(
            "Airport capacity degradation reduces arrival flexibility."
        )

    if stressed_sectors:
        causal_chain.append(
            "Holding/deviation pressure is increasing demand "
            "in already stressed sectors."
        )

    if target_data.get(
        "status"
    ) == "DEGRADED":
        causal_chain.append(
            (
                f"{target_flight_id} is operationally degraded "
                "and requires investigation."
            )
        )

    if network_results:
        causal_chain.append(
            "Network-level pressure confirms that the disruption "
            "extends beyond the target flight."
        )

    if not causal_chain:
        causal_chain.append(
            "Insufficient evidence to establish a complete causal chain."
        )

    if (
        target_data.get(
            "status"
        ) == "DEGRADED"
        and (
            severe_weather
            or stressed_sectors
            or degraded_airports
        )
    ):
        urgency = "HIGH"
    else:
        urgency = "MEDIUM"

    summary = (
        f"{target_flight_id} is degrading due to "
        f"{primary_cause.lower().replace('_', ' ')}. "
    )

    if degraded_airports:
        summary += (
            "Destination capacity degradation is limiting "
            "arrival flexibility. "
        )

    if stressed_sectors:
        summary += (
            "Network pressure is also building in "
            f"{len(stressed_sectors)} stressed sector(s). "
        )

    summary += (
        "The intervention decision should therefore account "
        "for both target-flight and surrounding-network conditions."
    )

    return Diagnosis(
        summary=summary,
        primary_cause=primary_cause,
        secondary_causes=secondary_causes,
        affected_flights=[
            target_flight_id
        ],
        affected_sectors=affected_sectors,
        affected_airports=affected_airports,
        urgency=urgency,
        evidence_completeness=(
            evidence_completeness
        ),
        causal_chain=causal_chain,
        causal_graph=graph,
        evidence_ids=evidence_ids,
    )