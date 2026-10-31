"""Price cache in front of the PriceProvider.

Prices live in the `prices` table. For each ticker the cache remembers only the
first and last cached date, and fetches what lies outside those bounds. Holes
inside the bounds are not chased: a missing weekday is almost always a market
holiday, and re-requesting it would cost a network call every time.
"""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.db.models import Price
from app.errors import UnknownTickers
from app.services.price_provider import PriceProvider

logger = logging.getLogger(__name__)

# A stock listed a few days after the requested start is not "missing" its early history.
HEAD_TOLERANCE_DAYS = 7


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    rows_fetched: int = 0


def missing_ranges(
    bounds: tuple[date, date] | None, start: date, end: date
) -> list[tuple[date, date]]:
    """Date ranges that must be fetched to cover start..end given cached bounds."""
    if bounds is None:
        return [(start, end)]
    first, last = bounds
    ranges: list[tuple[date, date]] = []
    if first > start + timedelta(days=HEAD_TOLERANCE_DAYS):
        ranges.append((start, first - timedelta(days=1)))
    latest_trading_day = pd.offsets.BDay().rollback(pd.Timestamp(end)).date()
    if last < latest_trading_day:
        ranges.append((last + timedelta(days=1), end))
    return ranges


class DataService:
    def __init__(
        self,
        session: Session,
        provider: PriceProvider,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._session = session
        self._provider = provider
        self.today = today
        self.stats = CacheStats()

    def get_prices(
        self, tickers: Iterable[str], start: date, end: date | None = None
    ) -> dict[str, pd.Series]:
        """Adjusted close series per ticker, fetching only what is not cached.

        Raises UnknownTickers listing every ticker that has no data at all.
        """
        end = end or self.today()
        before = CacheStats(self.stats.hits, self.stats.misses, self.stats.rows_fetched)
        prices: dict[str, pd.Series] = {}
        unknown: list[str] = []
        for ticker in dict.fromkeys(tickers):
            self._ensure_cached(ticker, start, end)
            series = self._load(ticker, start, end)
            if series.empty:
                unknown.append(ticker)
            else:
                prices[ticker] = series
        logger.info(
            "price cache",
            extra={
                "cache_hits": self.stats.hits - before.hits,
                "cache_misses": self.stats.misses - before.misses,
                "rows_fetched": self.stats.rows_fetched - before.rows_fetched,
            },
        )
        if unknown:
            raise UnknownTickers(unknown)
        return prices

    def _bounds(self, ticker: str) -> tuple[date, date] | None:
        row = self._session.execute(
            select(func.min(Price.date), func.max(Price.date)).where(Price.ticker == ticker)
        ).one()
        return None if row[0] is None else (row[0], row[1])

    def _ensure_cached(self, ticker: str, start: date, end: date) -> None:
        ranges = missing_ranges(self._bounds(ticker), start, end)
        if not ranges:
            self.stats.hits += 1
            return
        self.stats.misses += 1
        for range_start, range_end in ranges:
            self._store(ticker, self._provider.fetch(ticker, range_start, range_end))

    def _store(self, ticker: str, series: pd.Series) -> None:
        if series.empty:
            return
        dates = [timestamp.date() for timestamp in series.index]
        already_stored = set(
            self._session.scalars(
                select(Price.date).where(
                    Price.ticker == ticker, Price.date.between(min(dates), max(dates))
                )
            )
        )
        rows = [
            {"ticker": ticker, "date": day, "adj_close": float(value)}
            for day, value in zip(dates, series, strict=True)
            if day not in already_stored
        ]
        if rows:
            self._session.execute(insert(Price), rows)
            self._session.commit()
        self.stats.rows_fetched += len(rows)

    def _load(self, ticker: str, start: date, end: date) -> pd.Series:
        rows = self._session.execute(
            select(Price.date, Price.adj_close)
            .where(Price.ticker == ticker, Price.date.between(start, end))
            .order_by(Price.date)
        ).all()
        if not rows:
            return pd.Series(dtype=float, name=ticker)
        return pd.Series(
            [row.adj_close for row in rows],
            index=pd.DatetimeIndex([row.date for row in rows]),
            name=ticker,
        )
