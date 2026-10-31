import numpy as np
import pandas as pd
import pytest

from app.core.metrics import (
    annualized_return,
    annualized_volatility,
    beta,
    correlation,
    drawdown_curve,
    max_drawdown,
    sharpe_ratio,
)
from app.core.returns import log_returns


def _returns_from_prices(prices: list[float]) -> pd.Series:
    """Daily log returns of a price path; the index starts one day after the first price."""
    index = pd.bdate_range("2024-01-01", periods=len(prices))
    return log_returns(pd.DataFrame({"P": prices}, index=index))["P"]


def test_annualized_volatility_and_return() -> None:
    returns = pd.Series([0.01, -0.01, 0.02, 0.0, -0.02])
    assert annualized_volatility(returns) == pytest.approx(returns.std(ddof=1) * np.sqrt(252))
    assert annualized_return(pd.Series([0.001, 0.003])) == pytest.approx(0.002 * 252)


def test_sharpe_ratio() -> None:
    assert sharpe_ratio(0.10, 0.20, 0.04) == pytest.approx(0.3)


def test_sharpe_ratio_undefined_for_zero_volatility() -> None:
    assert sharpe_ratio(0.10, 0.0, 0.04) is None


def test_max_drawdown_finds_deepest_fall_and_dates() -> None:
    returns = _returns_from_prices([100, 120, 90, 95, 130, 104])
    result = max_drawdown(returns)
    # 120 -> 90 is a 25% fall; the later 130 -> 104 is only 20%
    assert result.depth == pytest.approx(0.25)
    assert result.peak_date == returns.index[0]
    assert result.trough_date == returns.index[1]


def test_max_drawdown_from_initial_value() -> None:
    returns = _returns_from_prices([100, 90, 95, 80])
    result = max_drawdown(returns)
    assert result.depth == pytest.approx(0.20)
    assert result.peak_date == returns.index[0]
    assert result.trough_date == returns.index[2]


def test_drawdown_curve_is_never_positive() -> None:
    returns = _returns_from_prices([100, 105, 99, 110, 108])
    assert (drawdown_curve(returns) <= 1e-12).all()


def test_drawdown_of_rising_series_is_zero() -> None:
    returns = _returns_from_prices([100, 101, 102, 103])
    assert max_drawdown(returns).depth == pytest.approx(0.0)


def test_beta_and_correlation_of_scaled_benchmark() -> None:
    rng = np.random.default_rng(1)
    bench = pd.Series(rng.normal(0, 0.01, 200), index=pd.bdate_range("2024-01-01", periods=200))
    portfolio = 1.5 * bench
    assert beta(portfolio, bench) == pytest.approx(1.5)
    assert correlation(portfolio, bench) == pytest.approx(1.0)


def test_beta_uses_only_overlapping_dates() -> None:
    index = pd.bdate_range("2024-01-01", periods=10)
    bench = pd.Series(np.linspace(-0.02, 0.02, 10), index=index)
    portfolio = (2 * bench).iloc[2:]
    assert beta(portfolio, bench) == pytest.approx(2.0)


def test_beta_undefined_when_benchmark_is_flat() -> None:
    index = pd.bdate_range("2024-01-01", periods=5)
    flat = pd.Series(0.001, index=index)
    moving = pd.Series([0.01, -0.01, 0.02, 0.0, -0.02], index=index)
    assert beta(moving, flat) is None
    assert correlation(moving, flat) is None
    assert correlation(flat, moving) is None
