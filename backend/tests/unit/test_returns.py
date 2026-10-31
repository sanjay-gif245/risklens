import numpy as np
import pandas as pd
import pytest

from app.core.returns import (
    align_prices,
    log_returns,
    portfolio_returns,
    split_by_history,
    weights_from_values,
)


def test_log_returns_match_definition() -> None:
    prices = pd.DataFrame(
        {"X": [100.0, 110.0, 99.0]}, index=pd.bdate_range("2024-01-01", periods=3)
    )
    result = log_returns(prices)
    assert len(result) == 2
    assert result["X"].iloc[0] == pytest.approx(np.log(1.1))
    assert result["X"].iloc[1] == pytest.approx(np.log(99 / 110))


def test_log_returns_reject_non_positive_prices() -> None:
    prices = pd.DataFrame({"X": [100.0, 0.0]}, index=pd.bdate_range("2024-01-01", periods=2))
    with pytest.raises(ValueError, match="strictly positive"):
        log_returns(prices)


def test_align_prices_fills_short_gap_and_drops_long_one() -> None:
    dates = pd.bdate_range("2024-01-01", periods=12)
    full = pd.Series(np.arange(1.0, 13.0), index=dates)
    gappy = full.copy()
    gappy.iloc[2:4] = np.nan  # two missing days: a holiday, filled
    gappy.iloc[6:11] = np.nan  # five missing days: only three can be filled
    result = align_prices({"A": full, "B": gappy})

    assert result.loc[dates[2], "B"] == gappy.iloc[1]
    assert result.loc[dates[8], "B"] == gappy.iloc[5]
    assert dates[9] not in result.index
    assert dates[10] not in result.index
    assert dates[11] in result.index


def test_align_prices_trims_to_common_history() -> None:
    dates = pd.bdate_range("2024-01-01", periods=6)
    old = pd.Series(1.0, index=dates)
    young = pd.Series(2.0, index=dates[3:])
    result = align_prices({"OLD": old, "YOUNG": young})
    assert list(result.index) == list(dates[3:])


def test_split_by_history_reports_short_tickers() -> None:
    long = pd.Series(1.0, index=pd.bdate_range("2022-01-01", periods=300))
    short = pd.Series(1.0, index=pd.bdate_range("2024-01-01", periods=100))
    usable, too_short = split_by_history({"LONG": long, "SHORT": short})
    assert list(usable) == ["LONG"]
    assert too_short == {"SHORT": 100}


def test_weights_from_values_sum_to_one() -> None:
    weights = weights_from_values(pd.Series({"A": 600.0, "B": 400.0}))
    assert weights["A"] == pytest.approx(0.6)
    assert weights.sum() == pytest.approx(1.0)


def test_weights_from_values_reject_empty_value() -> None:
    with pytest.raises(ValueError):
        weights_from_values(pd.Series({"A": 0.0}))


def test_portfolio_returns_is_weighted_sum(
    hand_returns: pd.DataFrame, hand_weights: pd.Series
) -> None:
    result = portfolio_returns(hand_returns, hand_weights)
    assert result.iloc[0] == pytest.approx(0.6 * 0.01 + 0.4 * 0.02)
    assert result.iloc[4] == pytest.approx(-0.02)


def test_portfolio_returns_reject_mismatched_tickers(hand_returns: pd.DataFrame) -> None:
    with pytest.raises(ValueError):
        portfolio_returns(hand_returns, pd.Series({"A": 1.0}))
