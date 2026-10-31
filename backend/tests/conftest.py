"""Shared test data and fakes. Nothing here touches the network."""

from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import Engine, StaticPool, create_engine
from sqlalchemy.orm import Session

from app.db.models import Base
from app.errors import ProviderUnavailable
from app.services.data_service import DataService

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_LAST_DAY = date(2023, 12, 29)


@pytest.fixture
def hand_returns() -> pd.DataFrame:
    """The five-day, two-stock table from docs/hand_calculation.md."""
    dates = pd.bdate_range("2024-01-01", periods=5)
    return pd.DataFrame(
        {
            "A": np.array([1, -1, 2, 0, -2]) / 100,
            "B": np.array([2, -2, 1, 1, -2]) / 100,
        },
        index=dates,
    )


@pytest.fixture
def hand_weights() -> pd.Series:
    return pd.Series({"A": 0.6, "B": 0.4})


@pytest.fixture
def make_returns() -> Callable[..., pd.DataFrame]:
    """Factory for seeded, reproducible random daily returns."""

    def build(
        n_days: int = 600, n_assets: int = 3, seed: int = 7, vol: float = 0.01
    ) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        data = rng.normal(0.0003, vol, size=(n_days, n_assets))
        columns = [f"S{i}" for i in range(n_assets)]
        return pd.DataFrame(
            data, index=pd.bdate_range("2021-01-01", periods=n_days), columns=columns
        )

    return build


class FakePriceProvider:
    """Serves prices from a wide DataFrame and records every request."""

    def __init__(self, prices: pd.DataFrame, failing: set[str] | None = None) -> None:
        self.prices = prices
        self.failing = failing or set()
        self.calls: list[tuple[str, date, date]] = []

    def fetch(self, ticker: str, start: date, end: date) -> pd.Series:
        self.calls.append((ticker, start, end))
        if ticker in self.failing:
            raise ProviderUnavailable(f"fake outage for {ticker}")
        if ticker not in self.prices.columns:
            return pd.Series(dtype=float, name=ticker)
        window = self.prices.loc[pd.Timestamp(start) : pd.Timestamp(end), ticker]
        return window.dropna()


@pytest.fixture(scope="session")
def synthetic_prices() -> pd.DataFrame:
    """Seeded synthetic prices for US-style and Indian-style tickers (see fixtures/README.md)."""
    return pd.read_csv(FIXTURES / "synthetic_prices.csv", index_col="date", parse_dates=True)


@pytest.fixture
def provider(synthetic_prices: pd.DataFrame) -> FakePriceProvider:
    return FakePriceProvider(synthetic_prices)


@pytest.fixture
def engine() -> Iterator[Engine]:
    """In-memory SQLite; the schema is created from the models."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def data_service(session: Session, provider: FakePriceProvider) -> DataService:
    return DataService(session, provider, today=lambda: FIXTURE_LAST_DAY)
