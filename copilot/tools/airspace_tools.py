from typing import Any

from copilot.mock_engine import MockEngineClient

from .base import AerisTool, ToolResult


class GetAirspaceStateTool(AerisTool):
    name = "get_airspace_state"

    description = (
        "Retrieve the current simulated airspace state, "
        "including target-flight status, aircraft count, "
        "weather, airports and sectors."
    )

    def __init__(
        self,
        engine: MockEngineClient,
    ) -> None:
        self.engine = engine

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def execute(
        self,
        **kwargs: Any,
    ) -> ToolResult:
        state = self.engine.get_state()

        return ToolResult.success(
            tool_name=self.name,
            summary=(
                "Current simulated airspace state retrieved."
            ),
            data=state,
            evidence=[
                {
                    "kind": "OBSERVATION",
                    "title": "Airspace state",
                    "summary": (
                        "Current simulated network state "
                        "was retrieved from the engine."
                    ),
                }
            ],
        )


class GetDisruptionsTool(AerisTool):
    name = "get_disruptions"

    description = (
        "Retrieve active simulated disruptions and alerts "
        "affecting flights, sectors or airports."
    )

    def __init__(
        self,
        engine: MockEngineClient,
    ) -> None:
        self.engine = engine

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def execute(
        self,
        **kwargs: Any,
    ) -> ToolResult:
        disruptions = (
            self.engine.get_disruptions()
        )

        return ToolResult.success(
            tool_name=self.name,
            summary=(
                f"Retrieved {len(disruptions)} active disruptions."
            ),
            data={
                "disruptions": disruptions
            },
            evidence=[
                {
                    "kind": "DISRUPTION",
                    "title": "Active disruptions",
                    "summary": (
                        f"{len(disruptions)} active disruption "
                        "signals are available."
                    ),
                }
            ],
        )


class GetTargetFlightTool(AerisTool):
    name = "get_target_flight"

    description = (
        "Retrieve the current operational state of a target flight."
    )

    def __init__(
        self,
        engine: MockEngineClient,
    ) -> None:
        self.engine = engine

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "flight_id": {
                    "type": "string",
                    "description": (
                        "Identifier of the flight to inspect."
                    ),
                }
            },
            "required": [
                "flight_id"
            ],
        }

    def execute(
        self,
        flight_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        flight = (
            self.engine.get_target_flight(
                flight_id
            )
        )

        if flight is None:
            return ToolResult.failure(
                tool_name=self.name,
                error_code="FLIGHT_NOT_FOUND",
                error_message=(
                    f"Flight {flight_id} was not found."
                ),
                summary=(
                    "Target flight could not be found."
                ),
            )

        return ToolResult.success(
            tool_name=self.name,
            summary=(
                f"Operational state retrieved for {flight_id}."
            ),
            data={
                "flight": flight
            },
            evidence=[
                {
                    "kind": "FLIGHT_STATE",
                    "title": f"{flight_id} state",
                    "summary": (
                        f"Current operational state of {flight_id}."
                    ),
                }
            ],
        )


class GetSectorStateTool(AerisTool):
    name = "get_sector_state"

    description = (
        "Retrieve current and projected traffic/capacity "
        "for the specified airspace sector."
    )

    def __init__(
        self,
        engine: MockEngineClient,
    ) -> None:
        self.engine = engine

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sector_id": {
                    "type": "string",
                    "description": "Sector identifier.",
                }
            },
            "required": [
                "sector_id"
            ],
        }

    def execute(
        self,
        sector_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        sector = (
            self.engine.get_sector_state(
                sector_id
            )
        )

        if sector is None:
            return ToolResult.failure(
                tool_name=self.name,
                error_code="SECTOR_NOT_FOUND",
                error_message=(
                    f"Sector {sector_id} was not found."
                ),
                summary=(
                    "Requested sector does not exist."
                ),
            )

        return ToolResult.success(
            tool_name=self.name,
            summary=(
                f"Sector {sector_id} state retrieved."
            ),
            data={
                "sector": sector
            },
            evidence=[
                {
                    "kind": "SECTOR_STATE",
                    "title": f"{sector_id} capacity",
                    "summary": (
                        f"Projected utilization for {sector_id}: "
                        f"{sector.get('projected_utilization', 'N/A')}."
                    ),
                    "candidate_id": None,
                }
            ],
        )


class GetAirportStateTool(AerisTool):
    name = "get_airport_state"

    description = (
        "Retrieve operational status and capacity "
        "for a simulated airport."
    )

    def __init__(
        self,
        engine: MockEngineClient,
    ) -> None:
        self.engine = engine

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "airport_id": {
                    "type": "string",
                    "description": "Airport identifier.",
                }
            },
            "required": [
                "airport_id"
            ],
        }

    def execute(
        self,
        airport_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        airport = (
            self.engine.get_airport_state(
                airport_id
            )
        )

        if airport is None:
            return ToolResult.failure(
                tool_name=self.name,
                error_code="AIRPORT_NOT_FOUND",
                error_message=(
                    f"Airport {airport_id} was not found."
                ),
                summary=(
                    "Requested airport does not exist."
                ),
            )

        return ToolResult.success(
            tool_name=self.name,
            summary=(
                f"Airport {airport_id} state retrieved."
            ),
            data={
                "airport": airport
            },
            evidence=[
                {
                    "kind": "AIRPORT_STATE",
                    "title": f"{airport_id} operational state",
                    "summary": (
                        f"{airport_id} status: "
                        f"{airport.get('operational_status', 'UNKNOWN')}."
                    ),
                }
            ],
        )


def build_airspace_tools(
    engine: MockEngineClient,
) -> list[AerisTool]:
    return [
        GetAirspaceStateTool(engine),
        GetDisruptionsTool(engine),
        GetTargetFlightTool(engine),
        GetSectorStateTool(engine),
        GetAirportStateTool(engine),
    ]