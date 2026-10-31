"""Covariance of daily returns: a plain Python loop against pandas and NumPy.

The risk figures all start from the covariance matrix, so this is the hot path
that decides how large a portfolio the service can handle.

Run from the repository root:
    backend/.venv/bin/python benchmarks/covariance_bench.py
"""

import platform
import time
from collections.abc import Callable
from functools import partial

import numpy as np
import pandas as pd

DAYS = 756  # three years of trading days
SIZES = (5, 10, 25, 50, 100)
LOOP_REPEATS = 3
VECTOR_REPEATS = 50


def covariance_loops(returns: list[list[float]]) -> list[list[float]]:
    """Sample covariance written the way the formula reads, with explicit loops."""
    days = len(returns)
    assets = len(returns[0])
    means = [sum(row[j] for row in returns) / days for j in range(assets)]
    cov = [[0.0] * assets for _ in range(assets)]
    for i in range(assets):
        for j in range(i, assets):
            total = 0.0
            for row in returns:
                total += (row[i] - means[i]) * (row[j] - means[j])
            cov[i][j] = cov[j][i] = total / (days - 1)
    return cov


def best_seconds(func: Callable[[], object], repeats: int) -> float:
    """Fastest of several runs, which is the least affected by other work on the machine."""
    times = []
    for _ in range(repeats):
        started = time.perf_counter()
        func()
        times.append(time.perf_counter() - started)
    return min(times)


def main() -> None:
    rng = np.random.default_rng(0)
    print(f"Python {platform.python_version()}, NumPy {np.__version__}, pandas {pd.__version__}")
    print(f"{platform.platform()}, {platform.machine()}")
    print(f"{DAYS} days of returns per asset")
    print(f"best of {LOOP_REPEATS} runs (loop), best of {VECTOR_REPEATS} (numpy, pandas)\n")
    header = ("assets", "python loop", "numpy.cov", "DataFrame.cov", "loop / numpy")
    print(f"{header[0]:>6} {header[1]:>13} {header[2]:>11} {header[3]:>14} {header[4]:>13}")

    for assets in SIZES:
        data = rng.normal(0.0, 0.01, size=(DAYS, assets))
        frame = pd.DataFrame(data)
        rows = data.tolist()

        # The three implementations must agree before their speed means anything
        assert np.allclose(covariance_loops(rows), np.cov(data, rowvar=False))
        assert np.allclose(frame.cov().to_numpy(), np.cov(data, rowvar=False))

        loop = best_seconds(partial(covariance_loops, rows), LOOP_REPEATS)
        vector = best_seconds(partial(np.cov, data, rowvar=False), VECTOR_REPEATS)
        pandas_cov = best_seconds(frame.cov, VECTOR_REPEATS)
        print(
            f"{assets:>6} {loop * 1000:>11.2f}ms {vector * 1000:>9.3f}ms "
            f"{pandas_cov * 1000:>12.3f}ms {loop / vector:>12.0f}x"
        )


if __name__ == "__main__":
    main()
