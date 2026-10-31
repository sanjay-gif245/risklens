"""Value at Risk and expected shortfall.

Conventions used throughout:
  * VaR and CVaR are positive numbers: a loss of 2% is returned as 0.02.
  * Returns are daily log returns, so the base horizon is one day.
  * A horizon of h days is obtained by multiplying the 1-day figure by
    sqrt(h). That assumes independent daily returns; it is a simplification.
"""

from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy import stats

VarMethod = Literal["historical", "parametric", "monte_carlo"]

DEFAULT_SIMULATIONS = 10_000
DEFAULT_SEED = 42

FloatArray = NDArray[np.float64]


def _check_confidence(confidence: float) -> None:
    if not 0.5 < confidence < 1.0:
        raise ValueError("confidence must be between 0.5 and 1 (exclusive)")


def _check_horizon(horizon: int) -> None:
    if horizon < 1:
        raise ValueError("horizon must be at least 1 day")


def historical_var(returns: FloatArray, confidence: float, horizon: int = 1) -> float:
    """Empirical percentile of past returns.

    VaR = -percentile(returns, 100 * (1 - confidence)), then scaled by
    sqrt(horizon). Makes no distribution assumption, but only knows about the
    losses that happened in the sample window.
    """
    _check_confidence(confidence)
    _check_horizon(horizon)
    threshold = np.percentile(returns, 100 * (1 - confidence))
    return float(-threshold * np.sqrt(horizon))


def parametric_var_from_moments(
    mean: float, std: float, confidence: float, horizon: int = 1
) -> float:
    """Normal-distribution VaR: -(mean + z * std), with z = Phi^-1(1 - confidence).

    Assumes returns are normal. Real returns have fatter tails, so this tends
    to understate the loss at high confidence levels.
    """
    _check_confidence(confidence)
    _check_horizon(horizon)
    z = stats.norm.ppf(1 - confidence)
    return float(-(mean + z * std) * np.sqrt(horizon))


def parametric_var(returns: FloatArray, confidence: float, horizon: int = 1) -> float:
    """Parametric VaR from the sample mean and sample standard deviation."""
    return parametric_var_from_moments(
        float(np.mean(returns)), float(np.std(returns, ddof=1)), confidence, horizon
    )


def historical_cvar(returns: FloatArray, confidence: float, horizon: int = 1) -> float:
    """Expected shortfall: average loss on the days at or beyond the VaR cut-off.

    VaR says where the tail starts; CVaR says how bad it is once you are in it.
    """
    _check_confidence(confidence)
    _check_horizon(horizon)
    cutoff = np.percentile(returns, 100 * (1 - confidence))
    tail = returns[returns <= cutoff]
    return float(-np.mean(tail) * np.sqrt(horizon))


def standard_normals(n_simulations: int, n_assets: int, seed: int = DEFAULT_SEED) -> FloatArray:
    """Independent N(0, 1) draws with a fixed seed so results are reproducible."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n_simulations, n_assets))


def _cholesky(cov: FloatArray) -> FloatArray:
    """Lower-triangular L with L @ L.T == cov.

    Perfectly correlated assets give a singular covariance matrix, which plain
    Cholesky rejects. A tiny diagonal jitter, scaled to the matrix, fixes that
    without visibly changing the result.
    """
    scale = max(float(np.mean(np.diag(cov))), 1e-12)
    for jitter in (0.0, 1e-12, 1e-10, 1e-8):
        try:
            return np.linalg.cholesky(cov + np.eye(cov.shape[0]) * scale * jitter)
        except np.linalg.LinAlgError:
            continue
    raise ValueError("covariance matrix is not positive semi-definite")


def simulate_portfolio_returns(
    mean: FloatArray, cov: FloatArray, weights: FloatArray, normals: FloatArray
) -> FloatArray:
    """Simulated 1-day portfolio returns from a multivariate normal.

    Correlated asset returns are mean + L z, where z are independent standard
    normals and L is the Cholesky factor of the covariance matrix. The
    portfolio return is the weighted sum across assets.
    """
    factor = _cholesky(cov)
    asset_returns = mean + normals @ factor.T
    return np.asarray(asset_returns @ weights, dtype=np.float64)
