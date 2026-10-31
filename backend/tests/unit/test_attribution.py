from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

from app.core.attribution import correlation_matrix, risk_contributions
from app.core.metrics import portfolio_volatility


def test_contributions_sum_to_portfolio_volatility(
    make_returns: Callable[..., pd.DataFrame],
) -> None:
    returns = make_returns(n_days=500, n_assets=6, seed=21)
    weights = pd.Series([0.30, 0.25, 0.20, 0.15, 0.07, 0.03], index=returns.columns)
    cov = returns.cov()
    table = risk_contributions(cov, weights)
    assert table["contribution"].sum() == pytest.approx(portfolio_volatility(cov, weights))
    assert table["pct_contribution"].sum() == pytest.approx(1.0)


def test_single_stock_carries_all_the_risk(make_returns: Callable[..., pd.DataFrame]) -> None:
    returns = make_returns(n_days=300, n_assets=1)
    table = risk_contributions(returns.cov(), pd.Series({"S0": 1.0}))
    assert table["pct_contribution"]["S0"] == pytest.approx(1.0)
    assert table["contribution"]["S0"] == pytest.approx(returns["S0"].std(ddof=1) * np.sqrt(252))


def test_identical_stocks_share_risk_in_proportion_to_weight() -> None:
    series = pd.Series([0.01, -0.02, 0.015, -0.005, 0.0, 0.012])
    returns = pd.DataFrame({"X": series, "Y": series})
    table = risk_contributions(returns.cov(), pd.Series({"X": 0.7, "Y": 0.3}))
    assert table["pct_contribution"]["X"] == pytest.approx(0.7)
    assert table["pct_contribution"]["Y"] == pytest.approx(0.3)


def test_small_volatile_position_can_dominate_risk() -> None:
    rng = np.random.default_rng(2)
    calm = rng.normal(0, 0.005, 400)
    wild = rng.normal(0, 0.04, 400)
    table = risk_contributions(
        pd.DataFrame({"CALM": calm, "WILD": wild}).cov(), pd.Series({"CALM": 0.9, "WILD": 0.1})
    )
    assert table["pct_contribution"]["WILD"] > table["weight"]["WILD"] * 3


def test_zero_variance_portfolio_is_rejected() -> None:
    returns = pd.DataFrame({"X": [0.0, 0.0, 0.0], "Y": [0.0, 0.0, 0.0]})
    with pytest.raises(ValueError, match="zero variance"):
        risk_contributions(returns.cov(), pd.Series({"X": 0.5, "Y": 0.5}))


def test_correlation_matrix_has_unit_diagonal(make_returns: Callable[..., pd.DataFrame]) -> None:
    matrix = correlation_matrix(make_returns(n_assets=4))
    assert np.allclose(np.diag(matrix.to_numpy()), 1.0)
    assert np.allclose(matrix.to_numpy(), matrix.to_numpy().T)
