"""Shared test data."""

from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def hand_returns() -> pd.DataFrame:
    """The five-day, two-stock table from docs/hand_calculation.md."""
    dates = pd.bdate_range("2024-01-01", periods=5)
    return pd.DataFrame(
        {
            "A": np.array([1, -1, 2, 0, -2]) / 100,
            "B": np.array([2, -2, 1, 1, -2]) / 100,
        },
        index=dates,
    )


@pytest.fixture
def hand_weights() -> pd.Series:
    return pd.Series({"A": 0.6, "B": 0.4})


@pytest.fixture
def make_returns() -> Callable[..., pd.DataFrame]:
    """Factory for seeded, reproducible random daily returns."""

    def build(
        n_days: int = 600, n_assets: int = 3, seed: int = 7, vol: float = 0.01
    ) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        data = rng.normal(0.0003, vol, size=(n_days, n_assets))
        columns = [f"S{i}" for i in range(n_assets)]
        return pd.DataFrame(
            data, index=pd.bdate_range("2021-01-01", periods=n_days), columns=columns
        )

    return build
