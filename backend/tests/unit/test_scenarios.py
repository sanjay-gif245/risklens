import numpy as np
import pandas as pd
import pytest

from app.core.scenarios import custom_shocks, historical_replay, market_shock


def test_market_shock_uses_each_holdings_beta() -> None:
    values = pd.Series({"A": 6000.0, "B": 4000.0})
    betas = pd.Series({"A": 1.2, "B": 0.8})
    result = market_shock(values, betas, -0.10)
    assert result.pnl == pytest.approx(-720.0 - 320.0)
    assert result.pnl_pct == pytest.approx(-0.104)
    assert result.breakdown.loc["A", "shock_return"] == pytest.approx(-0.12)


def test_market_shock_equals_portfolio_beta_times_shock() -> None:
    values = pd.Series({"A": 6000.0, "B": 4000.0})
    betas = pd.Series({"A": 1.2, "B": 0.8})
    portfolio_beta = 0.6 * 1.2 + 0.4 * 0.8
    assert market_shock(values, betas, 0.05).pnl_pct == pytest.approx(portfolio_beta * 0.05)


def test_market_shock_flags_holdings_without_a_beta() -> None:
    values = pd.Series({"A": 5000.0, "B": 5000.0})
    result = market_shock(values, pd.Series({"A": 1.0}), -0.2)
    assert not result.breakdown.loc["B", "covered"]
    assert result.covered_value == pytest.approx(5000.0)
    assert result.pnl_pct == pytest.approx(-0.2)


def test_custom_shocks_leave_other_holdings_untouched() -> None:
    values = pd.Series({"A": 1000.0, "B": 3000.0})
    result = custom_shocks(values, {"A": -0.5})
    assert result.pnl == pytest.approx(-500.0)
    assert result.pnl_pct == pytest.approx(-500.0 / 4000.0)
    assert result.breakdown.loc["B", "pnl"] == 0.0


def test_custom_shocks_reject_unknown_ticker() -> None:
    with pytest.raises(ValueError, match="ZZZ"):
        custom_shocks(pd.Series({"A": 1000.0}), {"ZZZ": -0.1})


def test_historical_replay_covers_only_holdings_that_existed() -> None:
    dates = pd.bdate_range("2020-02-19", "2020-03-23")
    old = pd.Series(np.linspace(100.0, 70.0, len(dates)), index=dates)
    new = pd.Series(50.0, index=dates[15:])  # listed mid-window
    prices = pd.DataFrame({"OLD": old, "NEW": new})
    values = pd.Series({"OLD": 8000.0, "NEW": 2000.0})

    result = historical_replay(values, prices, dates[0], dates[-1])

    assert result.breakdown.loc["OLD", "covered"]
    assert not result.breakdown.loc["NEW", "covered"]
    assert result.covered_value == pytest.approx(8000.0)
    assert result.pnl == pytest.approx(8000.0 * (70.0 / 100.0 - 1.0))
    assert result.pnl_pct == pytest.approx(-0.30)


def test_historical_replay_ignores_missing_columns() -> None:
    dates = pd.bdate_range("2022-01-03", periods=10)
    prices = pd.DataFrame({"A": np.linspace(10, 9, 10)}, index=dates)
    result = historical_replay(pd.Series({"A": 100.0, "B": 100.0}), prices, dates[0], dates[-1])
    assert result.breakdown["covered"].to_dict() == {"A": True, "B": False}
