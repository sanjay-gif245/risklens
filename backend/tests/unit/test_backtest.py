from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

from app.core.backtest import backtest_var, kupiec_pof, rolling_var
from app.core.returns import portfolio_returns
from app.core.var import VarMethod, historical_var, parametric_var

WINDOW = 250


def test_kupiec_exact_expected_rate_gives_zero_statistic() -> None:
    result = kupiec_pof(breaches=5, observations=100, confidence=0.95)
    assert result.likelihood_ratio == pytest.approx(0.0, abs=1e-12)
    assert result.p_value == pytest.approx(1.0)
    assert not result.rejected


def test_kupiec_zero_breaches_uses_the_limit_of_the_formula() -> None:
    # x = 0: LR = -2 * N * ln(1 - p) = -2 * 250 * ln(0.95)
    result = kupiec_pof(breaches=0, observations=250, confidence=0.95)
    assert result.likelihood_ratio == pytest.approx(-2 * 250 * np.log(0.95))
    assert result.rejected
    assert "overly cautious" in result.verdict


def test_kupiec_too_many_breaches_is_rejected_as_understating_risk() -> None:
    result = kupiec_pof(breaches=20, observations=250, confidence=0.99)
    assert result.rejected
    assert "understates risk" in result.verdict
    assert result.observed_rate == pytest.approx(0.08)
    assert result.expected_rate == pytest.approx(0.01)


def test_kupiec_accepted_verdict_mentions_counts() -> None:
    result = kupiec_pof(breaches=2, observations=100, confidence=0.95)
    assert result.verdict.startswith("Model accepted at the 5% significance level")
    assert "2 breaches in 100 days" in result.verdict


def test_kupiec_all_days_breached_is_handled() -> None:
    result = kupiec_pof(breaches=10, observations=10, confidence=0.95)
    assert result.p_value < 0.001


@pytest.mark.parametrize(("breaches", "observations"), [(-1, 10), (11, 10), (0, 0)])
def test_kupiec_rejects_impossible_counts(breaches: int, observations: int) -> None:
    with pytest.raises(ValueError):
        kupiec_pof(breaches, observations, 0.95)


def test_rolling_historical_var_uses_only_the_previous_window(
    make_returns: Callable[..., pd.DataFrame],
) -> None:
    returns = make_returns(n_days=400, n_assets=2)
    weights = pd.Series({"S0": 0.5, "S1": 0.5})
    series = rolling_var(returns, weights, "historical", 0.95, WINDOW)
    port = portfolio_returns(returns, weights).to_numpy()

    assert len(series) == 400 - WINDOW
    assert series.index[0] == returns.index[WINDOW]
    assert series.iloc[0] == pytest.approx(historical_var(port[:WINDOW], 0.95))
    assert series.iloc[-1] == pytest.approx(historical_var(port[-WINDOW - 1 : -1], 0.95))


def test_rolling_parametric_var_matches_direct_calculation(
    make_returns: Callable[..., pd.DataFrame],
) -> None:
    returns = make_returns(n_days=400, n_assets=2)
    weights = pd.Series({"S0": 0.3, "S1": 0.7})
    series = rolling_var(returns, weights, "parametric", 0.99, WINDOW)
    port = portfolio_returns(returns, weights).to_numpy()
    assert series.iloc[10] == pytest.approx(parametric_var(port[10 : WINDOW + 10], 0.99))


def test_rolling_monte_carlo_tracks_parametric(make_returns: Callable[..., pd.DataFrame]) -> None:
    returns = make_returns(n_days=300, n_assets=3)
    weights = pd.Series({"S0": 0.4, "S1": 0.4, "S2": 0.2})
    monte_carlo = rolling_var(returns, weights, "monte_carlo", 0.95, WINDOW, n_simulations=20_000)
    parametric = rolling_var(returns, weights, "parametric", 0.95, WINDOW)
    assert len(monte_carlo) == len(parametric) == 50
    assert np.allclose(monte_carlo.to_numpy(), parametric.to_numpy(), rtol=0.05)


@pytest.mark.parametrize("method", ["historical", "parametric", "monte_carlo"])
def test_todays_return_never_leaks_into_todays_var(
    make_returns: Callable[..., pd.DataFrame], method: VarMethod
) -> None:
    returns = make_returns(n_days=270, n_assets=2)
    weights = pd.Series({"S0": 0.5, "S1": 0.5})
    baseline = rolling_var(returns, weights, method, 0.95, WINDOW, n_simulations=2000)
    shocked_returns = returns.copy()
    shocked_returns.iloc[-1] = -0.5
    shocked = rolling_var(shocked_returns, weights, method, 0.95, WINDOW, n_simulations=2000)
    assert shocked.iloc[-1] == pytest.approx(baseline.iloc[-1])


def test_backtest_counts_are_consistent(make_returns: Callable[..., pd.DataFrame]) -> None:
    returns = make_returns(n_days=800, n_assets=3, seed=5)
    weights = pd.Series({"S0": 0.5, "S1": 0.3, "S2": 0.2})
    result = backtest_var(returns, weights, "historical", 0.95, WINDOW)

    assert result.kupiec.observations == len(result.var_series) == 800 - WINDOW
    assert result.kupiec.breaches == len(result.breach_dates)
    breached = result.realized < -result.var_series
    assert list(result.realized.index[breached]) == result.breach_dates
    assert 0.0 <= result.kupiec.p_value <= 1.0


def test_well_calibrated_model_is_not_rejected() -> None:
    rng = np.random.default_rng(99)
    returns = pd.DataFrame(
        rng.normal(0, 0.01, size=(2500, 1)),
        index=pd.bdate_range("2010-01-01", periods=2500),
        columns=["X"],
    )
    result = backtest_var(returns, pd.Series({"X": 1.0}), "parametric", 0.95, WINDOW)
    assert not result.kupiec.rejected
    assert result.kupiec.observed_rate == pytest.approx(0.05, abs=0.015)


def test_model_blind_to_a_volatility_jump_is_rejected() -> None:
    rng = np.random.default_rng(3)
    calm = rng.normal(0, 0.005, 400)
    stressed = rng.normal(0, 0.03, 150)
    values = np.concatenate([calm, stressed]).reshape(-1, 1)
    returns = pd.DataFrame(values, index=pd.bdate_range("2020-01-01", periods=550), columns=["X"])
    result = backtest_var(returns, pd.Series({"X": 1.0}), "historical", 0.99, WINDOW)
    assert result.kupiec.rejected
    assert "understates risk" in result.kupiec.verdict


def test_backtest_needs_more_history_than_the_window(
    make_returns: Callable[..., pd.DataFrame],
) -> None:
    returns = make_returns(n_days=WINDOW, n_assets=1)
    with pytest.raises(ValueError, match="need more than"):
        backtest_var(returns, pd.Series({"S0": 1.0}), "historical", 0.95, WINDOW)
