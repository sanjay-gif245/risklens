import uuid
from datetime import date

from pydantic import BaseModel

from app.core.var import VarMethod


class BacktestMethodResult(BaseModel):
    method: VarMethod
    confidence: float
    observations: int
    breaches: int
    expected_rate: float
    observed_rate: float
    likelihood_ratio: float
    p_value: float
    rejected: bool
    verdict: str
    breach_dates: list[date]
    var: list[float]  # one value per entry of BacktestResponse.dates, positive loss fraction


class BacktestResponse(BaseModel):
    portfolio_id: uuid.UUID
    window: int
    start_date: date
    end_date: date
    dates: list[date]
    realized_returns: list[float]  # daily portfolio log return, aligned with dates
    results: list[BacktestMethodResult]
    warnings: list[str]
