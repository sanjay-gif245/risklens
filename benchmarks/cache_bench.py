"""Cold fetch from Yahoo Finance against a load from the Postgres price cache.

Needs network access and the database from the README (DATABASE_URL, migrations
applied). It first deletes the cached prices of the benchmark tickers, which is
safe: the cache refills itself on the next request.

Run from the repository root:
    backend/.venv/bin/python benchmarks/cache_bench.py
"""

import platform
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db.models import Price
from app.db.session import get_engine
from app.services.data_service import DataService
from app.services.portfolio_service import history_start
from app.services.price_provider import YFinanceProvider
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

TICKERS = ["AAPL", "MSFT", "JPM", "XOM", "JNJ", "NVDA", "KO", "TSLA", "^GSPC"]
WARM_RUNS = 30


def main() -> None:
    with Session(get_engine()) as session:
        session.execute(delete(Price).where(Price.ticker.in_(TICKERS)))
        session.commit()

        data = DataService(session, YFinanceProvider())
        start = history_start(data.today())

        started = time.perf_counter()
        data.get_prices(TICKERS, start)
        cold = time.perf_counter() - started
        rows = session.scalar(
            select(func.count()).select_from(Price).where(Price.ticker.in_(TICKERS))
        )

        warm_times = []
        for _ in range(WARM_RUNS):
            started = time.perf_counter()
            DataService(session, YFinanceProvider()).get_prices(TICKERS, start)
            warm_times.append(time.perf_counter() - started)

    warm = statistics.median(warm_times)
    print(f"{platform.platform()}, {platform.machine()}, Python {platform.python_version()}")
    print(f"{len(TICKERS)} tickers, {rows} price rows ({start} to today)\n")
    print(f"cold, Yahoo Finance + inserts : {cold:8.3f} s")
    print(f"warm, Postgres cache (median of {WARM_RUNS}): {warm * 1000:8.1f} ms")
    print(f"warm, fastest                 : {min(warm_times) * 1000:8.1f} ms")
    print(f"speed-up                      : {cold / warm:8.0f}x")


if __name__ == "__main__":
    main()
