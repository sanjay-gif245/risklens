from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from app.core.var import (
    historical_cvar,
    historical_var,
    parametric_var,
    parametric_var_from_moments,
    simulate_portfolio_returns,
    standard_normals,
)


def test_historical_var_reads_the_percentile() -> None:
    returns = np.linspace(-0.05, 0.05, 101)
    # the 5th percentile of 101 evenly spaced points is exactly element 5
    assert historical_var(returns, 0.95) == pytest.approx(0.045)
    assert historical_var(returns, 0.99) == pytest.approx(0.049)


def test_horizon_scales_with_square_root_of_time() -> None:
    returns = np.linspace(-0.05, 0.05, 101)
    assert historical_var(returns, 0.95, horizon=4) == pytest.approx(
        2 * historical_var(returns, 0.95)
    )
    assert parametric_var(returns, 0.95, horizon=9) == pytest.approx(
        3 * parametric_var(returns, 0.95)
    )


def test_parametric_var_from_moments() -> None:
    assert parametric_var_from_moments(0.0, 0.01, 0.95) == pytest.approx(0.01 * 1.644854, abs=1e-8)
    # a positive mean offsets the loss
    assert parametric_var_from_moments(0.001, 0.01, 0.95) == pytest.approx(0.01 * 1.644854 - 0.001)


@pytest.mark.parametrize("confidence", [0.5, 1.0, 1.2, 0.0])
def test_invalid_confidence_rejected(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        historical_var(np.zeros(10), confidence)


def test_invalid_horizon_rejected() -> None:
    with pytest.raises(ValueError, match="horizon"):
        parametric_var(np.array([0.01, -0.01, 0.0]), 0.95, horizon=0)


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_var_and_cvar_ordering_properties(seed: int) -> None:
    rng = np.random.default_rng(seed)
    returns = stats.t.rvs(df=3, size=1500, random_state=rng) * 0.01
    var95 = historical_var(returns, 0.95)
    var99 = historical_var(returns, 0.99)
    assert var99 >= var95
    assert historical_cvar(returns, 0.95) >= var95
    assert historical_cvar(returns, 0.99) >= var99
    assert parametric_var(returns, 0.99) >= parametric_var(returns, 0.95)


def test_cvar_averages_the_tail() -> None:
    returns = np.array([-0.10, -0.06, -0.02, 0.0, 0.01, 0.02, 0.03, 0.03, 0.04, 0.05])
    # 80% VaR cut-off sits between -0.06 and -0.02 at position 1.8 of 9 -> -0.0568..
    cutoff = np.percentile(returns, 20)
    tail = returns[returns <= cutoff]
    assert historical_cvar(returns, 0.80) == pytest.approx(-tail.mean())


def test_monte_carlo_matches_parametric_for_normal_inputs(hand_returns: pd.DataFrame) -> None:
    mean = np.array([0.0004, 0.0002])
    cov = hand_returns.cov().to_numpy()
    weights = np.array([0.6, 0.4])
    normals = standard_normals(400_000, 2, seed=11)
    simulated = simulate_portfolio_returns(mean, cov, weights, normals)

    port_mean = float(weights @ mean)
    port_std = float(np.sqrt(weights @ cov @ weights))
    expected = parametric_var_from_moments(port_mean, port_std, 0.95)
    assert historical_var(simulated, 0.95) == pytest.approx(expected, rel=0.01)


def test_monte_carlo_is_reproducible_for_a_fixed_seed() -> None:
    cov = np.array([[1e-4, 0.5e-4], [0.5e-4, 4e-4]])
    args = (np.zeros(2), cov, np.array([0.5, 0.5]))
    first = simulate_portfolio_returns(*args, standard_normals(1000, 2, seed=5))
    second = simulate_portfolio_returns(*args, standard_normals(1000, 2, seed=5))
    other = simulate_portfolio_returns(*args, standard_normals(1000, 2, seed=6))
    assert np.array_equal(first, second)
    assert not np.array_equal(first, other)


def test_perfectly_correlated_assets_do_not_break_cholesky() -> None:
    cov = np.array([[1e-4, 1e-4], [1e-4, 1e-4]])  # singular matrix
    simulated = simulate_portfolio_returns(
        np.zeros(2), cov, np.array([0.5, 0.5]), standard_normals(50_000, 2, seed=3)
    )
    assert simulated.std() == pytest.approx(0.01, rel=0.02)


def test_zero_variance_assets_simulate_to_their_mean() -> None:
    simulated = simulate_portfolio_returns(
        np.array([0.001]), np.zeros((1, 1)), np.array([1.0]), standard_normals(1000, 1, seed=3)
    )
    assert simulated.std() < 1e-9
    assert simulated.mean() == pytest.approx(0.001)


def test_covariance_that_is_not_positive_semi_definite_is_rejected() -> None:
    cov = np.array([[1.0, 2.0], [2.0, 1.0]])
    with pytest.raises(ValueError, match="positive semi-definite"):
        simulate_portfolio_returns(np.zeros(2), cov, np.array([0.5, 0.5]), standard_normals(10, 2))


def test_single_asset_with_full_weight_matches_its_own_var(
    make_returns: Callable[..., pd.DataFrame],
) -> None:
    series = make_returns(n_days=500, n_assets=1)["S0"]
    mean = np.array([series.mean()])
    cov = np.array([[series.var(ddof=1)]])
    simulated = simulate_portfolio_returns(mean, cov, np.array([1.0]), standard_normals(300_000, 1))
    assert historical_var(simulated, 0.99) == pytest.approx(
        parametric_var(series.to_numpy(), 0.99), rel=0.02
    )
