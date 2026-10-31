"""Stress scenarios: a benchmark shock, hand-picked shocks, or a historical replay."""

import uuid
from datetime import date

import pandas as pd

from app.core.metrics import beta
from app.core.scenarios import (
    ScenarioResult,
    custom_shocks,
    historical_replay,
    market_shock,
    replay_path,
)
from app.errors import InvalidRequest
from app.schemas.scenario import (
    CustomShockRequest,
    HistoricalReplayRequest,
    MarketShockRequest,
    PathPoint,
    ScenarioEvent,
    ScenarioHolding,
    ScenarioRequest,
    ScenarioResponse,
)
from app.services.data_service import DataService
from app.services.portfolio_service import MarketData

MIN_WINDOW_DAYS = 5

EVENTS = [
    ScenarioEvent(
        key="covid_crash_2020",
        label="COVID-19 crash",
        start_date=date(2020, 2, 19),
        end_date=date(2020, 3, 23),
        description="From the S&P 500 record high on 19 Feb 2020 to the market low on 23 Mar 2020.",
    ),
    ScenarioEvent(
        key="financial_crisis_2008",
        label="Global financial crisis",
        start_date=date(2008, 9, 12),
        end_date=date(2009, 3, 9),
        description="From the Friday before Lehman failed to the S&P 500 low of 9 Mar 2009.",
    ),
    ScenarioEvent(
        key="rate_shock_2022",
        label="2022 rate shock",
        start_date=date(2022, 1, 3),
        end_date=date(2022, 10, 12),
        description="From the first trading day of 2022 to the S&P 500 low of 12 Oct 2022.",
    ),
]
_EVENTS_BY_KEY = {event.key: event for event in EVENTS}

SINGLE_FACTOR_NOTE = (
    "Single-factor estimate: each holding moves by its beta to the benchmark times the shock. "
    "Anything specific to a stock, and any change in correlations during a crash, is ignored."
)


def run_scenario(
    portfolio_id: uuid.UUID, market: MarketData, data: DataService, request: ScenarioRequest
) -> ScenarioResponse:
    notes = [
        f"{ticker} is not included: it has too little price history to analyse."
        for ticker in market.excluded
    ]
    if isinstance(request, MarketShockRequest):
        return _market_shock(portfolio_id, market, request, notes)
    if isinstance(request, CustomShockRequest):
        return _custom_shocks(portfolio_id, market, request, notes)
    return _historical_replay(portfolio_id, market, data, request, notes)


def _market_shock(
    portfolio_id: uuid.UUID, market: MarketData, request: MarketShockRequest, notes: list[str]
) -> ScenarioResponse:
    betas = pd.Series(
        {
            ticker: beta(market.returns[ticker], market.benchmark_returns) or float("nan")
            for ticker in market.returns.columns
        }
    )
    result = market_shock(market.values, betas, request.benchmark_move)
    label = f"{market.benchmark} moves {request.benchmark_move:+.1%}"
    return _response(
        portfolio_id, market, "market_shock", label, result, [*notes, SINGLE_FACTOR_NOTE]
    )


def _custom_shocks(
    portfolio_id: uuid.UUID, market: MarketData, request: CustomShockRequest, notes: list[str]
) -> ScenarioResponse:
    try:
        result = custom_shocks(market.values, request.shocks)
    except ValueError as exc:
        raise InvalidRequest(str(exc)) from exc
    return _response(portfolio_id, market, "custom_shocks", "Custom shocks", result, notes)


def _historical_replay(
    portfolio_id: uuid.UUID,
    market: MarketData,
    data: DataService,
    request: HistoricalReplayRequest,
    notes: list[str],
) -> ScenarioResponse:
    if request.event is not None:
        event = _EVENTS_BY_KEY.get(request.event)
        if event is None:
            raise InvalidRequest(
                f"Unknown event '{request.event}'. Known events: {', '.join(_EVENTS_BY_KEY)}."
            )
        start, end, label = event.start_date, event.end_date, event.label
    else:
        assert request.start_date is not None and request.end_date is not None
        start, end = request.start_date, request.end_date
        label = f"{start.isoformat()} to {end.isoformat()}"
    if (end - start).days < MIN_WINDOW_DAYS:
        raise InvalidRequest(f"The window must be at least {MIN_WINDOW_DAYS} days long.")
    if end > data.today():
        raise InvalidRequest("The window ends in the future.")

    # strict=False: a stock that did not exist then is reported as not covered, not as an error
    prices = pd.DataFrame(data.get_prices(list(market.values.index), start, end, strict=False))
    result = historical_replay(market.values, prices, pd.Timestamp(start), pd.Timestamp(end))
    if result.covered_value == 0:
        raise InvalidRequest(
            f"None of the holdings has prices for {start.isoformat()} to {end.isoformat()}."
        )

    uncovered = [str(t) for t in result.breakdown.index[~result.breakdown["covered"]]]
    if uncovered:
        share = result.covered_value / float(market.values.sum())
        notes = [
            *notes,
            f"{', '.join(uncovered)} did not trade throughout this window. The result covers "
            f"the other holdings only ({share:.0%} of today's portfolio value).",
        ]
    path = replay_path(market.values, prices, result.breakdown["covered"])
    return _response(
        portfolio_id,
        market,
        "historical_replay",
        label,
        result,
        notes,
        start,
        end,
        [
            PathPoint(date=ts.date(), change=float(v))
            for ts, v in zip(path.index, path, strict=True)
        ],
    )


def _response(
    portfolio_id: uuid.UUID,
    market: MarketData,
    kind: str,
    label: str,
    result: ScenarioResult,
    notes: list[str],
    start: date | None = None,
    end: date | None = None,
    path: list[PathPoint] | None = None,
) -> ScenarioResponse:
    holdings = [
        ScenarioHolding(
            ticker=str(ticker),
            value=float(row.value),
            shock_return=float(row.shock_return),
            pnl=float(row.pnl),
            covered=bool(row.covered),
        )
        for ticker, row in result.breakdown.iterrows()
    ]
    return ScenarioResponse(
        portfolio_id=portfolio_id,
        type=kind,
        label=label,
        start_date=start,
        end_date=end,
        currency=market.currency,
        total_value=float(market.values.sum()),
        covered_value=result.covered_value,
        pnl=result.pnl,
        pnl_pct=result.pnl_pct,
        holdings=holdings,
        path=path or [],
        notes=notes,
    )
