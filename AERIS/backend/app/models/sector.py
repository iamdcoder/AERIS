from pydantic import BaseModel, ConfigDict, Field


class Sector(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    geometry: dict
    nodes: list[str] = Field(default_factory=list)
    capacity: int = Field(ge=0)
    current_traffic: int = Field(default=0, ge=0)
    forecast_traffic: int = Field(default=0, ge=0)
    utilization_pct: float = Field(default=0.0, ge=0)
