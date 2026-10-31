import uuid
from datetime import date

from pydantic import BaseModel

from app.core.var import VarMethod


class DrawdownOut(BaseModel):
    depth: float  # positive fraction, 0.25 means a 25% fall
    peak_date: date
    trough_date: date


class RiskSummary(BaseModel):
    annual_return: float
    annual_volatility: float
    sharpe_ratio: float | None
    risk_free_rate: float
    beta: float | None
    correlation_to_benchmark: float | None
    max_drawdown: DrawdownOut


class VarEstimate(BaseModel):
    """Losses are positive. CVaR is None where the method does not define it here."""

    method: VarMethod
    var_pct: float
    var_amount: float
    cvar_pct: float | None
    cvar_amount: float | None


class ContributionOut(BaseModel):
    ticker: str
    weight: float
    contribution: float  # annualized volatility units; sums to annual_volatility
    pct_contribution: float


class CorrelationOut(BaseModel):
    tickers: list[str]
    matrix: list[list[float]]


class DrawdownPoint(BaseModel):
    date: date
    drawdown: float  # zero or negative


class RiskResponse(BaseModel):
    portfolio_id: uuid.UUID
    currency: str
    benchmark: str
    portfolio_value: float
    as_of: date
    confidence: float
    horizon_days: int
    observations: int
    window_start: date
    window_end: date
    summary: RiskSummary
    var: list[VarEstimate]
    contributions: list[ContributionOut]
    correlation: CorrelationOut
    drawdown_curve: list[DrawdownPoint]
    excluded: dict[str, int]
    warnings: list[str]
