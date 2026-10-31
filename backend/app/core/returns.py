"""Price cleaning and return calculation.

Everything here is a pure function over pandas objects: no database, no web.
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 252
MAX_FFILL_DAYS = 3
MIN_HISTORY_DAYS = 252


def split_by_history(
    series: dict[str, pd.Series], min_days: int = MIN_HISTORY_DAYS
) -> tuple[dict[str, pd.Series], dict[str, int]]:
    """Separate tickers with enough price history from those without.

    Returns (usable, too_short) where too_short maps ticker -> number of
    observed prices. The caller must surface too_short to the user; a short
    history makes covariance estimates unreliable, so such stocks are left out
    of the calculation rather than silently included.
    """
    usable: dict[str, pd.Series] = {}
    too_short: dict[str, int] = {}
    for ticker, prices in series.items():
        observed = int(prices.dropna().shape[0])
        if observed >= min_days:
            usable[ticker] = prices
        else:
            too_short[ticker] = observed
    return usable, too_short


def align_prices(series: dict[str, pd.Series], max_ffill: int = MAX_FFILL_DAYS) -> pd.DataFrame:
    """Combine per-ticker price series onto one calendar.

    Holidays differ between markets and tickers, so a day can be missing for
    one ticker only. A gap of up to `max_ffill` days is filled with the last
    known price (a holiday, not a crash). Any day that is still incomplete is
    dropped, which also trims the sample to the period where every ticker
    exists: in effect an inner join with a small tolerance for holidays.
    """
    frame = pd.concat(series, axis=1).sort_index()
    frame = frame.ffill(limit=max_ffill)
    return frame.dropna(how="any")


def log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily log returns, ln(P_t / P_{t-1}).

    Log returns add up over time and stay symmetric for up and down moves,
    which is what the covariance and the Cholesky simulation assume.
    """
    if (prices <= 0).to_numpy().any():
        raise ValueError("prices must be strictly positive to take logs")
    logs = pd.DataFrame(np.log(prices.to_numpy()), index=prices.index, columns=prices.columns)
    return logs.diff().dropna(how="all")


def weights_from_values(values: pd.Series) -> pd.Series:
    """Portfolio weights from current market values (quantity x latest price)."""
    total = float(values.sum())
    if total <= 0:
        raise ValueError("portfolio value must be positive")
    return values / total


def portfolio_returns(returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Daily portfolio return series with constant weights.

    Assumption: weights stay fixed across the whole sample (no rebalancing
    drift). Asset log returns are combined linearly, which is a close
    approximation for daily moves.
    """
    if set(weights.index) != set(returns.columns):
        raise ValueError("weights and returns must cover the same tickers")
    aligned = weights.reindex(returns.columns)
    return pd.Series(returns.to_numpy() @ aligned.to_numpy(), index=returns.index, name="portfolio")
