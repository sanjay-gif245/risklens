import uuid
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, model_validator


class MarketShockRequest(BaseModel):
    type: Literal["market_shock"]
    benchmark_move: float = Field(ge=-0.9, le=1.0, description="0.10 means the benchmark rises 10%")


class CustomShockRequest(BaseModel):
    type: Literal["custom_shocks"]
    shocks: dict[str, Annotated[float, Field(ge=-1.0, le=10.0)]] = Field(
        min_length=1, description="ticker -> return, -0.30 means a 30% fall"
    )


class HistoricalReplayRequest(BaseModel):
    type: Literal["historical_replay"]
    event: str | None = Field(default=None, description="key from GET /api/scenario-events")
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def event_or_dates(self) -> Self:
        has_dates = self.start_date is not None or self.end_date is not None
        if self.event is not None and has_dates:
            raise ValueError("give either an event or start_date and end_date, not both")
        if self.event is None and (self.start_date is None or self.end_date is None):
            raise ValueError("give an event, or both start_date and end_date")
        return self


ScenarioRequest = Annotated[
    MarketShockRequest | CustomShockRequest | HistoricalReplayRequest,
    Field(discriminator="type"),
]


class ScenarioEvent(BaseModel):
    key: str
    label: str
    start_date: date
    end_date: date
    description: str


class ScenarioHolding(BaseModel):
    ticker: str
    value: float
    shock_return: float
    pnl: float
    covered: bool


class PathPoint(BaseModel):
    date: date
    change: float  # fraction of the covered starting value, 0.0 at the start


class ScenarioResponse(BaseModel):
    portfolio_id: uuid.UUID
    type: str
    label: str
    start_date: date | None
    end_date: date | None
    currency: str
    total_value: float
    covered_value: float
    pnl: float
    pnl_pct: float
    holdings: list[ScenarioHolding]
    path: list[PathPoint]
    notes: list[str]
