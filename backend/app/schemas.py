from datetime import date
from pydantic import BaseModel, Field


class DecisionRequest(BaseModel):
    route: str = Field(pattern=r"^[A-Z]{3}-[A-Z]{3}$")
    travel_date: date | None = None
    current_fare: float | None = Field(default=None, gt=0)
    advance_days: int = Field(default=7, ge=0, le=365)


class ScenarioRequest(BaseModel):
    route: str = Field(pattern=r"^[A-Z]{3}-[A-Z]{3}$")
    fare_change_pct: float = Field(ge=-80, le=300)
