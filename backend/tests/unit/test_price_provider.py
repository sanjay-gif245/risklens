from datetime import date
from typing import Any

import pandas as pd
import pytest

from app.errors import ProviderUnavailable
from app.services import price_provider
from app.services.price_provider import YFinanceProvider


def history_frame() -> pd.DataFrame:
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-03"], tz="America/New_York")
    return pd.DataFrame({"Close": [10.0, 11.0]}, index=index)


def script_yfinance(monkeypatch: pytest.MonkeyPatch, outcomes: list[Any]) -> list[dict[str, Any]]:
    """Make yf.Ticker(...).history() return or raise the given outcomes in order."""
    requests: list[dict[str, Any]] = []

    class ScriptedTicker:
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        def history(self, **kwargs: Any) -> pd.DataFrame:
            requests.append(kwargs)
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            assert isinstance(outcome, pd.DataFrame)
            return outcome

    monkeypatch.setattr(price_provider.yf, "Ticker", ScriptedTicker)
    return requests


def test_returns_timezone_free_series_and_asks_for_inclusive_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = script_yfinance(monkeypatch, [history_frame()])
    series = YFinanceProvider().fetch("AAPL", date(2024, 1, 1), date(2024, 1, 3))

    assert list(series.index) == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")]
    assert series.index.tz is None
    assert list(series) == [10.0, 11.0]
    assert requests[0]["end"] == date(2024, 1, 4)  # yfinance's end is exclusive
    assert requests[0]["auto_adjust"] is True


def test_empty_history_means_no_data_not_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    script_yfinance(monkeypatch, [pd.DataFrame()])
    assert YFinanceProvider().fetch("NOPE", date(2024, 1, 1), date(2024, 1, 3)).empty


def test_transient_failures_are_retried_with_exponential_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_yfinance(monkeypatch, [ConnectionError("reset"), TimeoutError("slow"), history_frame()])
    sleeps: list[float] = []
    provider = YFinanceProvider(attempts=3, backoff_seconds=1.0, sleep=sleeps.append)

    series = provider.fetch("AAPL", date(2024, 1, 1), date(2024, 1, 3))

    assert len(series) == 2
    assert sleeps == [1.0, 2.0]


def test_gives_up_with_a_clear_error_after_the_last_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = script_yfinance(monkeypatch, [ConnectionError("down")] * 3)
    sleeps: list[float] = []
    provider = YFinanceProvider(attempts=3, backoff_seconds=0.5, sleep=sleeps.append)

    with pytest.raises(ProviderUnavailable) as caught:
        provider.fetch("AAPL", date(2024, 1, 1), date(2024, 1, 3))

    assert len(requests) == 3
    assert sleeps == [0.5, 1.0]  # no sleep after the final failure
    assert "AAPL" in caught.value.message
    assert caught.value.status_code == 502
