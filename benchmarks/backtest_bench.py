"""Time of the rolling VaR backtest for each method.

Uses seeded synthetic returns so the result does not depend on the network or
the database. Each run covers about 530 test days at 95% confidence; the Monte
Carlo run re-estimates the covariance and simulates 10,000 paths every day.

Run from the repository root:
    backend/.venv/bin/python benchmarks/backtest_bench.py
"""

import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.backtest import backtest_var
from app.core.var import VarMethod

DAYS = 780
ASSETS = (8, 25, 50)
METHODS: tuple[VarMethod, ...] = ("historical", "parametric", "monte_carlo")
REPEATS = 3


def main() -> None:
    rng = np.random.default_rng(0)
    print(f"{platform.platform()}, {platform.machine()}, Python {platform.python_version()}")
    print(f"{DAYS} days of returns, window 250, best of {REPEATS}\n")
    print(f"{'assets':>6} {'historical':>12} {'parametric':>12} {'monte carlo':>13}")

    for assets in ASSETS:
        returns = pd.DataFrame(
            rng.normal(0.0004, 0.01, size=(DAYS, assets)),
            index=pd.bdate_range("2021-01-04", periods=DAYS),
        )
        weights = pd.Series(1.0 / assets, index=returns.columns)
        cells = []
        for method in METHODS:
            times = []
            for _ in range(REPEATS):
                started = time.perf_counter()
                backtest_var(returns, weights, method, 0.95)
                times.append(time.perf_counter() - started)
            cells.append(min(times))
        hist, param, mc = (cell * 1000 for cell in cells)
        print(f"{assets:>6} {hist:>10.1f}ms {param:>10.1f}ms {mc:>11.1f}ms")


if __name__ == "__main__":
    main()
