from pydantic import BaseModel, ConfigDict


class WeatherCell(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    geometry: dict
    intensity: str
    movement: dict
    uncertainty: float
    type: str
    active: bool = True
