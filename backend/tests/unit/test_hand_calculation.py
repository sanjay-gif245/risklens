"""Reproduces docs/hand_calculation.md number for number."""

import numpy as np
import pandas as pd
import pytest

from app.core.attribution import risk_contributions
from app.core.backtest import kupiec_pof
from app.core.metrics import portfolio_volatility
from app.core.returns import TRADING_DAYS, portfolio_returns
from app.core.var import historical_cvar, historical_var, parametric_var


def test_covariance_matrix(hand_returns: pd.DataFrame) -> None:
    cov = hand_returns.cov()
    assert cov.loc["A", "A"] == pytest.approx(0.00025)
    assert cov.loc["B", "B"] == pytest.approx(0.00035)
    assert cov.loc["A", "B"] == pytest.approx(0.00025)


def test_portfolio_volatility(hand_returns: pd.DataFrame, hand_weights: pd.Series) -> None:
    cov = hand_returns.cov()
    daily = portfolio_volatility(cov, hand_weights) / np.sqrt(TRADING_DAYS)
    assert daily == pytest.approx(0.0163095, abs=1e-7)
    assert portfolio_volatility(cov, hand_weights) == pytest.approx(0.258905, abs=1e-6)


def test_parametric_var(hand_returns: pd.DataFrame, hand_weights: pd.Series) -> None:
    series = portfolio_returns(hand_returns, hand_weights).to_numpy()
    assert parametric_var(series, 0.95) == pytest.approx(0.026827, abs=1e-6)
    assert parametric_var(series, 0.99) == pytest.approx(0.037942, abs=1e-6)


def test_historical_var_and_cvar(hand_returns: pd.DataFrame, hand_weights: pd.Series) -> None:
    series = portfolio_returns(hand_returns, hand_weights).to_numpy()
    assert historical_var(series, 0.95) == pytest.approx(0.0188)
    assert historical_cvar(series, 0.95) == pytest.approx(0.020)


def test_risk_contributions(hand_returns: pd.DataFrame, hand_weights: pd.Series) -> None:
    table = risk_contributions(hand_returns.cov(), hand_weights)
    daily = table["contribution"] / np.sqrt(TRADING_DAYS)
    assert daily["A"] == pytest.approx(0.00919709, abs=1e-8)
    assert daily["B"] == pytest.approx(0.00711242, abs=1e-8)
    assert table["pct_contribution"]["A"] == pytest.approx(0.563910, abs=1e-6)
    assert table["pct_contribution"]["B"] == pytest.approx(0.436090, abs=1e-6)


def test_kupiec_hand_case() -> None:
    result = kupiec_pof(breaches=2, observations=100, confidence=0.95)
    assert result.likelihood_ratio == pytest.approx(2.4286, abs=1e-3)
    assert result.p_value == pytest.approx(0.1191, abs=1e-3)
    assert not result.rejected
