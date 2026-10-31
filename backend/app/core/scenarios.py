"""Stress scenarios applied to current holdings.

Each function takes the current market value of every holding and returns a
per-holding breakdown plus the portfolio total. Values are in the portfolio's
currency; returns are simple fractions (-0.10 is a 10% fall).
"""

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

# A stock whose first price comes more than this many calendar days after the
# window start is treated as not having existed at the time of the event.
START_TOLERANCE_DAYS = 4


@dataclass(frozen=True)
class ScenarioResult:
    """Outcome of one scenario.

    breakdown has one row per holding with columns: value, shock_return, pnl,
    covered. pnl_pct is relative to the value of the covered holdings, which
    equals the whole portfolio unless some holdings could not be shocked.
    """

    breakdown: pd.DataFrame
    pnl: float
    pnl_pct: float
    covered_value: float


def _summarise(values: pd.Series, shock_return: pd.Series, covered: pd.Series) -> ScenarioResult:
    pnl = values * shock_return
    breakdown = pd.DataFrame(
        {"value": values, "shock_return": shock_return, "pnl": pnl, "covered": covered}
    )
    covered_value = float(values[covered].sum())
    total_pnl = float(pnl[covered].sum())
    pnl_pct = total_pnl / covered_value if covered_value > 0 else 0.0
    return ScenarioResult(breakdown, total_pnl, pnl_pct, covered_value)


def market_shock(
    values: pd.Series, holding_betas: pd.Series, benchmark_move: float
) -> ScenarioResult:
    """Benchmark moves by `benchmark_move`; each holding moves by beta_i * move.

    Single-factor model: it assumes the benchmark explains each stock's move
    and ignores everything specific to the stock. Because beta is linear in
    the weights, the portfolio move equals portfolio beta times the shock.
    """
    betas = holding_betas.reindex(values.index)
    covered = betas.notna()
    shock = (betas * benchmark_move).fillna(0.0)
    return _summarise(values, shock, covered)


def custom_shocks(values: pd.Series, shocks: Mapping[str, float]) -> ScenarioResult:
    """Apply a user-chosen return to named tickers; the rest are unchanged."""
    unknown = set(shocks) - set(values.index)
    if unknown:
        raise ValueError(f"shocks given for tickers not in the portfolio: {sorted(unknown)}")
    shock = pd.Series(0.0, index=values.index)
    for ticker, move in shocks.items():
        shock[ticker] = move
    return _summarise(values, shock, pd.Series(True, index=values.index))


def historical_replay(
    values: pd.Series, prices: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
) -> ScenarioResult:
    """Replay what each holding actually did between `start` and `end`.

    `prices` holds the event-window prices (columns are tickers, NaN where a
    stock had no price). Each holding's return is last price / first price - 1,
    applied to today's market value, i.e. "if I held today's portfolio then".
    Holdings that did not exist at the start or end of the window are marked
    not covered and left out of the totals instead of being guessed.
    """
    shock = pd.Series(0.0, index=values.index)
    covered = pd.Series(False, index=values.index)
    for ticker in values.index:
        if ticker not in prices.columns:
            continue
        series = prices[ticker].dropna()
        if series.empty:
            continue
        starts_in_time = (series.index[0] - start).days <= START_TOLERANCE_DAYS
        ends_in_time = (end - series.index[-1]).days <= START_TOLERANCE_DAYS
        if starts_in_time and ends_in_time:
            shock[ticker] = float(series.iloc[-1] / series.iloc[0] - 1.0)
            covered[ticker] = True
    return _summarise(values, shock, covered)
