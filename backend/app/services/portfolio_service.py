"""Portfolio storage and the market data every analysis starts from."""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.returns import (
    MIN_HISTORY_DAYS,
    align_prices,
    log_returns,
    split_by_history,
    weights_from_values,
)
from app.db.models import Holding, Portfolio
from app.errors import InsufficientData, InvalidPortfolioFile, PortfolioNotFound
from app.schemas.portfolio import HoldingOut, PortfolioDetail, PortfolioSummary
from app.services.csv_import import ParsedHoldings
from app.services.data_service import DataService
from app.services.markets import default_benchmark, single_currency

PRICE_BUFFER_DAYS = 10


def history_start(today: date) -> date:
    """First date to request so that `history_years` of trading days are covered."""
    return today - timedelta(days=get_settings().history_years * 365 + PRICE_BUFFER_DAYS)


def create_portfolio(
    session: Session,
    data: DataService,
    name: str,
    parsed: ParsedHoldings,
    benchmark: str | None,
) -> Portfolio:
    """Validate against real price data, then store the portfolio.

    Fetching prices here is what proves every ticker exists, and it warms the
    cache so the first analysis request is fast.
    """
    name = name.strip()
    if not name or len(name) > 100:
        raise InvalidPortfolioFile("Portfolio name must be 1 to 100 characters.")
    tickers = [holding.ticker for holding in parsed.holdings]
    currency = single_currency(tickers)
    benchmark_ticker = (benchmark or default_benchmark(currency)).strip().upper()
    data.get_prices([*tickers, benchmark_ticker], history_start(data.today()))

    portfolio = Portfolio(
        name=name,
        base_currency=currency,
        benchmark=benchmark_ticker,
        holdings=[
            Holding(ticker=h.ticker, quantity=h.quantity, buy_price=h.buy_price)
            for h in parsed.holdings
        ],
    )
    session.add(portfolio)
    session.commit()
    return portfolio


def short_history_warning(ticker: str, days: int) -> str:
    return (
        f"{ticker} excluded: only {days} trading days of price history "
        f"(at least {MIN_HISTORY_DAYS} are needed)."
    )


def summarise(portfolio: Portfolio) -> PortfolioSummary:
    return PortfolioSummary(
        id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_currency,
        benchmark=portfolio.benchmark,
        created_at=portfolio.created_at,
        holding_count=len(portfolio.holdings),
    )


def describe_portfolio(
    portfolio: Portfolio, data: DataService, notices: list[str] | None = None
) -> PortfolioDetail:
    """Holdings valued at their latest cached price, including ones too short to analyse."""
    series = data.get_prices(
        [holding.ticker for holding in portfolio.holdings], history_start(data.today())
    )
    last_prices = {ticker: float(prices.iloc[-1]) for ticker, prices in series.items()}
    total_value = sum(h.quantity * last_prices[h.ticker] for h in portfolio.holdings)
    total_cost = sum(h.quantity * h.buy_price for h in portfolio.holdings)

    rows: list[HoldingOut] = []
    warnings: list[str] = []
    for holding in portfolio.holdings:
        days = int(series[holding.ticker].shape[0])
        value = holding.quantity * last_prices[holding.ticker]
        cost = holding.quantity * holding.buy_price
        if days < MIN_HISTORY_DAYS:
            warnings.append(short_history_warning(holding.ticker, days))
        rows.append(
            HoldingOut(
                ticker=holding.ticker,
                quantity=holding.quantity,
                buy_price=holding.buy_price,
                last_price=last_prices[holding.ticker],
                market_value=value,
                cost_value=cost,
                unrealized_pnl=value - cost,
                weight=value / total_value,
                history_days=days,
                analysed=days >= MIN_HISTORY_DAYS,
            )
        )
    return PortfolioDetail(
        **summarise(portfolio).model_dump(),
        as_of=max(prices.index[-1] for prices in series.values()).date(),
        total_value=total_value,
        total_cost=total_cost,
        unrealized_pnl=total_value - total_cost,
        holdings=rows,
        warnings=warnings,
        notices=notices or [],
    )


def list_portfolios(session: Session) -> list[Portfolio]:
    return list(session.scalars(select(Portfolio).order_by(Portfolio.created_at.desc())))


def get_portfolio(session: Session, portfolio_id: uuid.UUID) -> Portfolio:
    portfolio = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise PortfolioNotFound(portfolio_id)
    return portfolio


def delete_portfolio(session: Session, portfolio_id: uuid.UUID) -> None:
    session.delete(get_portfolio(session, portfolio_id))
    session.commit()


@dataclass(frozen=True)
class MarketData:
    """Cleaned, aligned data for the holdings that can be analysed."""

    currency: str
    benchmark: str
    as_of: date
    returns: pd.DataFrame  # daily log returns, one column per included holding
    benchmark_returns: pd.Series
    prices: pd.DataFrame
    quantities: pd.Series
    buy_prices: pd.Series
    values: pd.Series  # quantity x latest price, in the portfolio currency
    weights: pd.Series
    excluded: dict[str, int]  # ticker -> trading days of history it has
    warnings: list[str]


def load_market_data(portfolio: Portfolio, data: DataService) -> MarketData:
    """Fetch, clean and align prices; derive returns, values and weights.

    Holdings with under 252 trading days of history are left out and reported
    in `warnings`, never silently dropped. The sample is cut to the dates on
    which every included holding and the benchmark have a price.
    """
    tickers = [holding.ticker for holding in portfolio.holdings]
    benchmark = portfolio.benchmark
    series = data.get_prices([*tickers, benchmark], history_start(data.today()))

    benchmark_days = int(series[benchmark].dropna().shape[0])
    if benchmark_days < MIN_HISTORY_DAYS:
        raise InsufficientData(
            f"Benchmark {benchmark} has only {benchmark_days} trading days of history; "
            f"at least {MIN_HISTORY_DAYS} are needed."
        )

    usable, too_short = split_by_history({ticker: series[ticker] for ticker in tickers})
    warnings = [short_history_warning(ticker, days) for ticker, days in too_short.items()]
    if not usable:
        raise InsufficientData(
            f"No holding has {MIN_HISTORY_DAYS} trading days of price history, so risk "
            "cannot be estimated.",
            {"excluded": too_short},
        )

    aligned = align_prices({**usable, benchmark: series[benchmark]})
    if len(aligned) <= MIN_HISTORY_DAYS:
        raise InsufficientData(
            f"Only {len(aligned)} trading days remain after aligning the holdings and the "
            f"benchmark; more than {MIN_HISTORY_DAYS} are needed."
        )
    longest = max(int(s.dropna().shape[0]) for s in [*usable.values(), series[benchmark]])
    if len(aligned) < 0.9 * longest:
        first_dates = {
            t: s.dropna().index[0] for t, s in {**usable, benchmark: series[benchmark]}.items()
        }
        limiting = max(first_dates, key=lambda t: first_dates[t])
        warnings.append(
            f"History is limited to {len(aligned)} trading days because {limiting} only has "
            f"prices since {first_dates[limiting].date().isoformat()}."
        )

    included = list(usable)
    all_returns = log_returns(aligned)
    holding_prices = aligned[included]
    quantities = pd.Series({h.ticker: h.quantity for h in portfolio.holdings}).reindex(included)
    buy_prices = pd.Series({h.ticker: h.buy_price for h in portfolio.holdings}).reindex(included)
    values = quantities * holding_prices.iloc[-1]

    return MarketData(
        currency=portfolio.base_currency,
        benchmark=benchmark,
        as_of=aligned.index[-1].date(),
        returns=all_returns[included],
        benchmark_returns=all_returns[benchmark],
        prices=holding_prices,
        quantities=quantities,
        buy_prices=buy_prices,
        values=values,
        weights=weights_from_values(values),
        excluded=too_short,
        warnings=warnings,
    )
