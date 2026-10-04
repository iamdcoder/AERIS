from pydantic import BaseModel, ConfigDict


class Restriction(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    region: dict
    active_from_min: int
    active_to_min: int
    reason: str
    min_altitude_ft: float | None = None
    max_altitude_ft: float | None = None
    active: bool = False
