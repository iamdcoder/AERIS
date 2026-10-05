from pydantic import BaseModel, ConfigDict
from .aircraft import Position


class Airport(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str = ""
    position: Position
    arrival_capacity: int
    departure_capacity: int
    weather_status: str = "NORMAL"
    operational_status: str = "NORMAL"
