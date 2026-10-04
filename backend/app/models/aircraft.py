from pydantic import BaseModel, ConfigDict, Field


class Position(BaseModel):
    lat: float
    lon: float


class Aircraft(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    callsign: str
    position: Position
    altitude_ft: float
    speed_kt: float
    heading_deg: float = 0.0
    route: list[str] = Field(default_factory=list)
    destination: str
    fuel_remaining_min: float
    burn_rate_min_per_min: float = 1.0
    performance_class: str = "MEDIUM"
    status: str = "AIRBORNE"

    # Internal deterministic simulation state.
    route_index: int = 0
    edge_progress_min: float = 0.0
    delay_min: float = 0.0
    planned_travel_time_min: float = 0.0
    airline: str = "SIM"
    tail_number: str = ""
    original_route: list[str] = Field(default_factory=list)
