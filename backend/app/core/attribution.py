"""Risk attribution: which holdings drive the portfolio volatility."""

import numpy as np
import pandas as pd

from app.core.returns import TRADING_DAYS


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Pairwise Pearson correlation of daily returns across holdings."""
    return returns.corr()


def risk_contributions(cov: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    """Split annualized portfolio volatility into per-holding contributions.

    With sigma_p = sqrt(w' S w), the contribution of holding i is

        component_i = w_i * (S w)_i / sigma_p

    These sum exactly to sigma_p (Euler decomposition), so each holding's share
    of risk can be read next to its share of capital. A small, highly
    correlated position can contribute far more risk than its weight suggests.

    `cov` is the daily covariance matrix; the output is annualized.
    Columns: weight, contribution (annualized vol units), pct_contribution.
    """
    tickers = list(cov.columns)
    w = weights.reindex(tickers).to_numpy()
    sigma_w = cov.to_numpy() @ w
    daily_variance = float(w @ sigma_w)
    if daily_variance <= 0:
        raise ValueError("portfolio has zero variance; contributions are undefined")
    daily_vol = np.sqrt(daily_variance)
    component = w * sigma_w / daily_vol * np.sqrt(TRADING_DAYS)
    annual_vol = daily_vol * np.sqrt(TRADING_DAYS)
    return pd.DataFrame(
        {
            "weight": w,
            "contribution": component,
            "pct_contribution": component / annual_vol,
        },
        index=tickers,
    )
