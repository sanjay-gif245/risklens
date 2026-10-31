"""Rolling VaR backtest with the Kupiec proportion-of-failures test.

For every day t after the first `window` days, VaR is estimated using only the
previous `window` days and compared with the return that actually happened on
day t. A breach is a day on which the loss exceeded the VaR.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import xlogy

from app.core.var import (
    DEFAULT_SEED,
    DEFAULT_SIMULATIONS,
    VarMethod,
    historical_var,
    simulate_portfolio_returns,
    standard_normals,
)

DEFAULT_WINDOW = 250
SIGNIFICANCE = 0.05


@dataclass(frozen=True)
class KupiecResult:
    """Kupiec proportion-of-failures likelihood-ratio test."""

    observations: int
    breaches: int
    expected_rate: float
    observed_rate: float
    likelihood_ratio: float
    p_value: float
    significance: float

    @property
    def rejected(self) -> bool:
        return self.p_value < self.significance

    @property
    def verdict(self) -> str:
        level = f"{self.significance:.0%}"
        counts = (
            f"{self.breaches} breaches in {self.observations} days, "
            f"{self.expected_rate * self.observations:.1f} expected (p = {self.p_value:.3f})"
        )
        if not self.rejected:
            return f"Model accepted at the {level} significance level: {counts}."
        if self.observed_rate > self.expected_rate:
            return (
                f"Model rejected at the {level} significance level, it understates risk: {counts}."
            )
        return f"Model rejected at the {level} significance level, it is overly cautious: {counts}."


def kupiec_pof(
    breaches: int, observations: int, confidence: float, significance: float = SIGNIFICANCE
) -> KupiecResult:
    """Kupiec (1995) proportion-of-failures test.

    Null hypothesis: the true breach probability equals p = 1 - confidence.
    With x breaches in N days and observed rate x/N,

        LR = -2 ln[(1-p)^(N-x) p^x] + 2 ln[(1-x/N)^(N-x) (x/N)^x]

    which is chi-square distributed with 1 degree of freedom under the null.
    A large LR means the observed breach rate is too far from p. The test is
    two-sided: too few breaches rejects as well as too many. xlogy treats
    0 * ln(0) as 0, which handles the x = 0 and x = N edge cases.
    """
    if observations <= 0:
        raise ValueError("need at least one observation")
    if not 0 <= breaches <= observations:
        raise ValueError("breaches must be between 0 and observations")
    p = 1 - confidence
    rate = breaches / observations
    log_null = xlogy(observations - breaches, 1 - p) + xlogy(breaches, p)
    log_alt = xlogy(observations - breaches, 1 - rate) + xlogy(breaches, rate)
    likelihood_ratio = float(max(-2 * (log_null - log_alt), 0.0))
    return KupiecResult(
        observations=observations,
        breaches=breaches,
        expected_rate=p,
        observed_rate=rate,
        likelihood_ratio=likelihood_ratio,
        p_value=float(stats.chi2.sf(likelihood_ratio, df=1)),
        significance=significance,
    )


def rolling_var(
    asset_returns: pd.DataFrame,
    weights: pd.Series,
    method: VarMethod,
    confidence: float,
    window: int = DEFAULT_WINDOW,
    n_simulations: int = DEFAULT_SIMULATIONS,
    seed: int = DEFAULT_SEED,
) -> pd.Series:
    """1-day VaR for each day, estimated from the `window` days before it.

    The result is indexed by the day the VaR applies to, so it lines up with
    the realized return of that day. The first `window` days have no estimate.
    """
    if len(asset_returns) <= window:
        raise ValueError(f"need more than {window} days of returns, got {len(asset_returns)}")
    w = weights.reindex(asset_returns.columns).to_numpy()
    portfolio = pd.Series(asset_returns.to_numpy() @ w, index=asset_returns.index)

    if method == "historical":
        # pandas interpolates linearly, the same rule as np.percentile
        cutoff = portfolio.rolling(window).quantile(1 - confidence).shift(1)
        return (-cutoff).dropna()
    if method == "parametric":
        z = stats.norm.ppf(1 - confidence)
        mean = portfolio.rolling(window).mean().shift(1)
        std = portfolio.rolling(window).std(ddof=1).shift(1)
        return (-(mean + z * std)).dropna()
    return _rolling_monte_carlo(asset_returns, w, confidence, window, n_simulations, seed)


def _rolling_monte_carlo(
    asset_returns: pd.DataFrame,
    w: np.ndarray,
    confidence: float,
    window: int,
    n_simulations: int,
    seed: int,
) -> pd.Series:
    """Monte Carlo VaR per day, re-estimating mean and covariance each time.

    The same standard-normal draws are reused every day (common random
    numbers), so day-to-day changes come from the data and not from sampling
    noise, and the loop stays fast.
    """
    values = asset_returns.to_numpy()
    normals = standard_normals(n_simulations, values.shape[1], seed)
    estimates = []
    for t in range(window, len(values)):
        past = values[t - window : t]
        simulated = simulate_portfolio_returns(
            past.mean(axis=0), np.atleast_2d(np.cov(past, rowvar=False)), w, normals
        )
        estimates.append(historical_var(simulated, confidence))
    return pd.Series(estimates, index=asset_returns.index[window:])


@dataclass(frozen=True)
class BacktestResult:
    method: VarMethod
    confidence: float
    window: int
    var_series: pd.Series
    realized: pd.Series
    breach_dates: list[pd.Timestamp]
    kupiec: KupiecResult


def backtest_var(
    asset_returns: pd.DataFrame,
    weights: pd.Series,
    method: VarMethod,
    confidence: float,
    window: int = DEFAULT_WINDOW,
    n_simulations: int = DEFAULT_SIMULATIONS,
    seed: int = DEFAULT_SEED,
) -> BacktestResult:
    """Run the rolling backtest for one method and confidence level."""
    var_series = rolling_var(
        asset_returns, weights, method, confidence, window, n_simulations, seed
    )
    w = weights.reindex(asset_returns.columns).to_numpy()
    realized_all = pd.Series(asset_returns.to_numpy() @ w, index=asset_returns.index)
    realized = realized_all.loc[var_series.index]
    breached = realized < -var_series
    return BacktestResult(
        method=method,
        confidence=confidence,
        window=window,
        var_series=var_series,
        realized=realized,
        breach_dates=list(realized.index[breached]),
        kupiec=kupiec_pof(int(breached.sum()), len(realized), confidence),
    )
