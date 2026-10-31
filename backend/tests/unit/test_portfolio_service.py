import uuid

import numpy as np
import pandas as pd
import pytest
from conftest import FIXTURE_LAST_DAY, FakePriceProvider
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Holding
from app.errors import InsufficientData, InvalidPortfolioFile, PortfolioNotFound, UnknownTickers
from app.services.csv_import import HoldingInput, ParsedHoldings
from app.services.data_service import DataService
from app.services.portfolio_service import (
    create_portfolio,
    delete_portfolio,
    get_portfolio,
    list_portfolios,
    load_market_data,
)


def parsed(*rows: tuple[str, float, float]) -> ParsedHoldings:
    return ParsedHoldings([HoldingInput(*row) for row in rows], [])


US = parsed(("AAA", 100, 100.0), ("BBB", 200, 50.0), ("CCC", 20, 240.0))


def test_us_portfolio_defaults_to_the_sp500_benchmark(
    session: Session, data_service: DataService
) -> None:
    portfolio = create_portfolio(session, data_service, " Growth ", US, None)
    assert portfolio.name == "Growth"
    assert portfolio.base_currency == "USD"
    assert portfolio.benchmark == "^GSPC"
    assert [h.ticker for h in portfolio.holdings] == ["AAA", "BBB", "CCC"]


def test_indian_portfolio_defaults_to_the_nifty_benchmark(
    session: Session, data_service: DataService
) -> None:
    portfolio = create_portfolio(
        session,
        data_service,
        "India",
        parsed(("RELI.NS", 10, 1900.0), ("TCSX.NS", 5, 3100.0)),
        None,
    )
    assert (portfolio.base_currency, portfolio.benchmark) == ("INR", "^NSEI")


def test_benchmark_can_be_overridden(session: Session, data_service: DataService) -> None:
    portfolio = create_portfolio(session, data_service, "P", US, " ^nsei ")
    assert portfolio.benchmark == "^NSEI"


def test_mixed_currencies_are_rejected_and_nothing_is_saved(
    session: Session, data_service: DataService
) -> None:
    mixed = parsed(("AAA", 1, 1.0), ("RELI.NS", 1, 1.0))
    with pytest.raises(InvalidPortfolioFile, match="Mixed currencies"):
        create_portfolio(session, data_service, "Mixed", mixed, None)
    assert list_portfolios(session) == []


def test_unknown_ticker_is_rejected_and_nothing_is_saved(
    session: Session, data_service: DataService
) -> None:
    with pytest.raises(UnknownTickers):
        create_portfolio(
            session, data_service, "Typo", parsed(("AAA", 1, 1.0), ("ZZZ", 1, 1.0)), None
        )
    assert list_portfolios(session) == []


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_portfolio_name_must_be_one_to_hundred_characters(
    session: Session, data_service: DataService, name: str
) -> None:
    with pytest.raises(InvalidPortfolioFile, match="name"):
        create_portfolio(session, data_service, name, US, None)


def test_get_list_and_delete(session: Session, data_service: DataService) -> None:
    first = create_portfolio(session, data_service, "First", US, None)
    second = create_portfolio(session, data_service, "Second", US, None)

    assert {p.name for p in list_portfolios(session)} == {"First", "Second"}
    assert get_portfolio(session, first.id).name == "First"

    delete_portfolio(session, first.id)
    assert [p.id for p in list_portfolios(session)] == [second.id]
    assert session.scalar(select(func.count()).select_from(Holding)) == 3  # only second's remain
    with pytest.raises(PortfolioNotFound):
        get_portfolio(session, first.id)


def test_unknown_portfolio_id_is_not_found(session: Session) -> None:
    with pytest.raises(PortfolioNotFound) as caught:
        get_portfolio(session, uuid.uuid4())
    assert caught.value.status_code == 404


def test_market_data_values_weights_and_alignment(
    session: Session, data_service: DataService, synthetic_prices: pd.DataFrame
) -> None:
    portfolio = create_portfolio(session, data_service, "P", US, None)
    market = load_market_data(portfolio, data_service)

    last = synthetic_prices.iloc[-1]
    assert market.as_of == FIXTURE_LAST_DAY
    assert market.values["AAA"] == pytest.approx(100 * last["AAA"])
    assert market.values["BBB"] == pytest.approx(200 * last["BBB"])
    assert market.weights.sum() == pytest.approx(1.0)
    assert market.weights["AAA"] == pytest.approx(market.values["AAA"] / market.values.sum())
    assert list(market.returns.columns) == ["AAA", "BBB", "CCC"]
    assert not market.returns.isna().any().any()  # BBB's two-day gap was filled
    assert market.returns.index.equals(market.benchmark_returns.index)
    assert market.warnings == []
    assert market.excluded == {}


def test_short_history_holdings_are_excluded_with_a_warning(
    session: Session, data_service: DataService
) -> None:
    holdings = parsed(("AAA", 10, 100.0), ("NEWCO", 10, 30.0))
    portfolio = create_portfolio(session, data_service, "P", holdings, None)
    market = load_market_data(portfolio, data_service)

    assert list(market.returns.columns) == ["AAA"]
    assert market.excluded == {"NEWCO": 120}
    assert market.weights["AAA"] == pytest.approx(1.0)
    assert market.warnings == [
        "NEWCO excluded: only 120 trading days of price history (at least 252 are needed)."
    ]


def test_portfolio_with_no_usable_holding_is_rejected(
    session: Session, data_service: DataService
) -> None:
    portfolio = create_portfolio(session, data_service, "P", parsed(("NEWCO", 10, 30.0)), None)
    with pytest.raises(InsufficientData, match="No holding"):
        load_market_data(portfolio, data_service)


def test_benchmark_with_short_history_is_rejected(
    session: Session, data_service: DataService
) -> None:
    portfolio = create_portfolio(session, data_service, "P", US, "NEWCO")
    with pytest.raises(InsufficientData, match="Benchmark NEWCO"):
        load_market_data(portfolio, data_service)


def test_shared_history_shorter_than_the_longest_is_reported(
    session: Session, synthetic_prices: pd.DataFrame
) -> None:
    prices = synthetic_prices[["AAA", "^GSPC"]].copy()
    prices["LATE"] = prices["AAA"] * 0.5
    prices.loc[prices.index[:380], "LATE"] = np.nan  # 400 days of history
    service = DataService(session, FakePriceProvider(prices), today=lambda: FIXTURE_LAST_DAY)

    portfolio = create_portfolio(
        session, service, "P", parsed(("AAA", 1, 1.0), ("LATE", 1, 1.0)), None
    )
    market = load_market_data(portfolio, service)

    assert len(market.returns) == 399
    assert any("limited to 400 trading days because LATE" in w for w in market.warnings)
