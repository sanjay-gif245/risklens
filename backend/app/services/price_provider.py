"""Where daily prices come from.

yfinance is an unofficial scraper of Yahoo Finance and breaks from time to
time, so the rest of the code depends on the small PriceProvider interface and
never on yfinance directly. Swapping the source means writing one class.
"""

import logging
import time
import warnings
from collections.abc import Callable
from datetime import date, timedelta
from typing import Protocol

import pandas as pd
import yfinance as yf

from app.errors import ProviderUnavailable

logger = logging.getLogger(__name__)


class PriceProvider(Protocol):
    def fetch(self, ticker: str, start: date, end: date) -> pd.Series:
        """Adjusted close by date for start..end inclusive; empty if the ticker has no data."""
        ...


class YFinanceProvider:
    def __init__(
        self,
        attempts: int = 3,
        backoff_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._attempts = attempts
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep

    def fetch(self, ticker: str, start: date, end: date) -> pd.Series:
        for attempt in range(1, self._attempts + 1):
            try:
                return self._download(ticker, start, end)
            except Exception as exc:  # yfinance raises many unrelated exception types
                logger.warning(
                    "price fetch failed",
                    extra={"ticker": ticker, "attempt": attempt, "error": str(exc)},
                )
                if attempt == self._attempts:
                    raise ProviderUnavailable(
                        f"Could not fetch prices for {ticker} after {self._attempts} attempts. "
                        "The price source may be down or rate limiting; try again shortly.",
                        {"ticker": ticker},
                    ) from exc
                self._sleep(self._backoff_seconds * 2 ** (attempt - 1))
        raise AssertionError("unreachable: the loop returns or raises")

    @staticmethod
    def _download(ticker: str, start: date, end: date) -> pd.Series:
        with warnings.catch_warnings():
            # yfinance still uses pandas options that pandas has deprecated
            warnings.filterwarnings("ignore", message=".*inplace.*")
            # yfinance treats `end` as exclusive
            history = yf.Ticker(ticker).history(
                start=start, end=end + timedelta(days=1), auto_adjust=True
            )
        if history.empty:
            return pd.Series(dtype=float, name=ticker)
        closes = history["Close"].dropna()
        index = pd.DatetimeIndex(closes.index).tz_localize(None).normalize()
        return pd.Series(closes.to_numpy(), index=index, name=ticker)
