from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class FlightIdRequest(BaseModel):
    flight_id: str = Field(..., description="Target flight identifier e.g. F102")


class AlternativesRequest(BaseModel):
    flight_id: str = Field(..., description="Target flight identifier e.g. F102")


class CandidateRequest(BaseModel):
    flight_id: str
    candidate_id: str
    route: list[str]
    speed_kt: float | None = None
    cruise_altitude_ft: float | None = None
    intervention_type: str = "reroute"

    class Config:
        extra = "allow"


class DecisionScoreRequest(BaseModel):
    candidates: list[dict[str, Any]] = Field(..., description="List of candidate intervention objects")


class ApplyRequest(BaseModel):
    candidate_id: str = Field(..., description="Candidate ID to apply e.g. ALT-D")
    approved: bool = Field(False, description="Explicit human approval flag. Must be true to apply.")


class VerifyRequest(BaseModel):
    candidate_id: str = Field(..., description="Candidate ID to verify e.g. ALT-D")


class CopilotRequest(BaseModel):
    target_flight_id: str = Field("F102", description="Target flight identifier")
    scenario_id: str = Field("mumbai_weather_crisis", description="Scenario identifier")
    run_id: str = Field("RUN-001", description="Run execution identifier")
