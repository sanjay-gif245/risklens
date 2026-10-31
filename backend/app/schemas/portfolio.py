import uuid
from datetime import date, datetime

from pydantic import BaseModel


class PortfolioSummary(BaseModel):
    id: uuid.UUID
    name: str
    base_currency: str
    benchmark: str
    created_at: datetime
    holding_count: int


class HoldingOut(BaseModel):
    ticker: str
    quantity: float
    buy_price: float
    last_price: float
    market_value: float
    cost_value: float
    unrealized_pnl: float
    weight: float  # share of total market value
    history_days: int
    analysed: bool  # False when the history is too short to be used in risk figures


class PortfolioDetail(PortfolioSummary):
    as_of: date
    total_value: float
    total_cost: float
    unrealized_pnl: float
    holdings: list[HoldingOut]
    warnings: list[str]
    notices: list[str] = []  # informational messages from the upload, such as merged rows
