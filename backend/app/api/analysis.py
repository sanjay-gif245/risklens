import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DataDep, SessionDep
from app.config import get_settings
from app.core.backtest import DEFAULT_WINDOW
from app.schemas.backtest import BacktestResponse
from app.schemas.risk import RiskResponse
from app.schemas.scenario import ScenarioEvent, ScenarioRequest, ScenarioResponse
from app.services import backtest_service, portfolio_service, risk_service, scenario_service

router = APIRouter(tags=["analysis"])


@router.get("/portfolios/{portfolio_id}/risk", response_model=RiskResponse)
def get_risk(
    portfolio_id: uuid.UUID,
    session: SessionDep,
    data: DataDep,
    confidence: Annotated[
        float, Query(ge=0.9, le=0.999, description="VaR confidence level")
    ] = 0.95,
    horizon: Annotated[int, Query(ge=1, le=30, description="Horizon in trading days")] = 1,
    lookback: Annotated[
        int | None, Query(ge=30, le=3000, description="Trading days of history to use")
    ] = None,
) -> RiskResponse:
    portfolio = portfolio_service.get_portfolio(session, portfolio_id)
    market = portfolio_service.load_market_data(portfolio, data)
    risk_free_rate = get_settings().risk_free_rate(portfolio.base_currency)
    return risk_service.compute_risk(
        portfolio.id, market, confidence, horizon, lookback, risk_free_rate
    )


@router.get("/scenario-events", response_model=list[ScenarioEvent])
def list_scenario_events() -> list[ScenarioEvent]:
    return scenario_service.EVENTS


@router.post("/portfolios/{portfolio_id}/scenario", response_model=ScenarioResponse)
def run_scenario(
    portfolio_id: uuid.UUID, body: ScenarioRequest, session: SessionDep, data: DataDep
) -> ScenarioResponse:
    portfolio = portfolio_service.get_portfolio(session, portfolio_id)
    market = portfolio_service.load_market_data(portfolio, data)
    return scenario_service.run_scenario(portfolio.id, market, data, body)


@router.get("/portfolios/{portfolio_id}/backtest", response_model=BacktestResponse)
def get_backtest(
    portfolio_id: uuid.UUID,
    session: SessionDep,
    data: DataDep,
    window: Annotated[
        int, Query(ge=60, le=750, description="Trading days used to estimate each day's VaR")
    ] = DEFAULT_WINDOW,
) -> BacktestResponse:
    portfolio = portfolio_service.get_portfolio(session, portfolio_id)
    market = portfolio_service.load_market_data(portfolio, data)
    return backtest_service.run_backtests(portfolio.id, market, window)
