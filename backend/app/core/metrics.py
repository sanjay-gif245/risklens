"""Headline performance and risk metrics for a daily portfolio return series."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.core.returns import TRADING_DAYS


@dataclass(frozen=True)
class Drawdown:
    """Deepest peak-to-trough fall of the portfolio value curve."""

    depth: float  # positive fraction, 0.25 means a 25% fall
    peak_date: pd.Timestamp
    trough_date: pd.Timestamp


def annualized_volatility(returns: pd.Series) -> float:
    """Sample standard deviation of daily returns, scaled by sqrt(252).

    Scaling by sqrt(time) assumes returns are independent from day to day.
    """
    return float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS))


def portfolio_volatility(cov: pd.DataFrame, weights: pd.Series) -> float:
    """Annualized volatility from the daily covariance matrix: sqrt(w' S w) * sqrt(252).

    Equals annualized_volatility of the portfolio return series when the same
    weights and sample covariance are used; this form shows where the
    diversification comes from (the off-diagonal covariance terms).
    """
    w = weights.reindex(cov.columns).to_numpy()
    return float(np.sqrt(w @ cov.to_numpy() @ w) * np.sqrt(TRADING_DAYS))


def annualized_return(returns: pd.Series) -> float:
    """Mean daily log return times 252 (an arithmetic annualization)."""
    return float(returns.mean() * TRADING_DAYS)


def sharpe_ratio(ann_return: float, ann_volatility: float, risk_free_rate: float) -> float | None:
    """(annualized return - risk-free rate) / annualized volatility.

    Returns None when volatility is zero, because the ratio is undefined.
    """
    if ann_volatility == 0:
        return None
    return (ann_return - risk_free_rate) / ann_volatility


def value_curve(returns: pd.Series) -> pd.Series:
    """Portfolio value path starting from 1.0 at the start of the sample.

    Built from cumulative log returns, so exp(cumsum) gives the growth of one
    unit of currency held with constant weights.
    """
    return pd.Series(np.exp(returns.cumsum().to_numpy()), index=returns.index)


def drawdown_curve(returns: pd.Series) -> pd.Series:
    """Drawdown at each date: value / running peak - 1 (zero or negative).

    The running peak starts at the initial value of 1.0, so a fall from the
    very first day counts as a drawdown too.
    """
    curve = value_curve(returns)
    running_peak = curve.cummax().clip(lower=1.0)
    return curve / running_peak - 1.0


def max_drawdown(returns: pd.Series) -> Drawdown:
    """Largest drawdown with the dates of its peak and trough.

    If the deepest fall starts from the initial value (the value never rose
    above 1.0 before the trough), the peak date is the first date in the sample.
    """
    curve = value_curve(returns)
    curve_with_start = pd.concat([pd.Series([1.0], index=[curve.index[0]]), curve])
    drawdowns = drawdown_curve(returns)
    trough_date: pd.Timestamp = drawdowns.index[int(np.argmin(drawdowns.to_numpy()))]
    depth = -float(drawdowns.min())
    up_to_trough = curve_with_start[:trough_date]
    peak_date: pd.Timestamp = up_to_trough.index[int(np.argmax(up_to_trough.to_numpy()))]
    return Drawdown(depth=depth, peak_date=peak_date, trough_date=trough_date)


def beta(portfolio: pd.Series, benchmark: pd.Series) -> float | None:
    """cov(portfolio, benchmark) / var(benchmark) on the overlapping dates.

    Returns None when the benchmark has no variance.
    """
    port, bench = portfolio.align(benchmark, join="inner")
    bench_var = float(bench.var(ddof=1))
    if bench_var == 0:
        return None
    return float(port.cov(bench) / bench_var)


def correlation(portfolio: pd.Series, benchmark: pd.Series) -> float | None:
    """Pearson correlation between portfolio and benchmark returns."""
    port, bench = portfolio.align(benchmark, join="inner")
    if port.std(ddof=1) == 0 or bench.std(ddof=1) == 0:
        return None
    return float(port.corr(bench))
