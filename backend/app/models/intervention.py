from pydantic import BaseModel, ConfigDict


class Intervention(BaseModel):
    model_config = ConfigDict(extra="allow")

    candidate_id: str
    flight_id: str
    intervention_type: str
    route: list[str]
    cruise_altitude_ft: float | None = None
    speed_kt: float | None = None
    timing_offset_min: float = 0.0
    hold_min: float = 0.0
