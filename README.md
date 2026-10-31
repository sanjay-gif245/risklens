# RiskLens

Portfolio risk, calculated the way a risk desk does it, then checked against history.

Upload a CSV of holdings (`ticker, quantity, buy_price`). RiskLens fetches three years of daily prices
and reports how risky the portfolio is, how much it could lose on a bad day, which holdings drive that
risk, how it would have fared in past crises, and whether its own VaR models actually held up: a rolling
backtest with the Kupiec likelihood-ratio test.

![Overview](docs/screenshots/overview.jpg)

| Risk | Scenarios | Backtest |
|---|---|---|
| ![Risk](docs/screenshots/risk.jpg) | ![Scenarios](docs/screenshots/scenarios.jpg) | ![Backtest](docs/screenshots/backtest.jpg) |

The screenshots show a demo portfolio of eight US large caps (`frontend/public/sample_portfolio.csv`)
with real prices fetched from Yahoo Finance.

## What it calculates

- **Volatility, return, Sharpe, maximum drawdown, beta and correlation** to a benchmark.
- **Value at risk** at 95% or 99%, over 1 to 30 days, three ways: historical, parametric (normal) and
  Monte Carlo (10,000 paths through a Cholesky factor). **Expected shortfall** (CVaR) beside it.
  Everything is shown as a percentage and as a currency amount.
- **Risk contribution** of each holding next to its weight, and a correlation matrix.
- **Scenarios:** a benchmark shock through beta, hand-picked shocks, and historical replay of the COVID
  crash, 2008 and the 2022 rate shock (or any dates) on today's holdings.
- **Backtest:** for each day, VaR is estimated from the previous 250 days and compared with that day's
  return. Breach counts, observed against expected rate, the Kupiec test and a plain-English verdict, for
  all three methods at both confidence levels.

Every formula, with its assumptions and failure modes, is in [docs/METHODOLOGY.md](docs/METHODOLOGY.md)
and on the Methodology page of the app.

## Run it locally

You need Python 3.12, Node 22 or newer, and PostgreSQL 16 (or Docker).

```bash
docker compose up -d db        # or: createdb risklens, with a local PostgreSQL
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env           # DATABASE_URL defaults to a local PostgreSQL named risklens
.venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --reload
cd ../frontend && npm ci && npm run dev
```

With `docker compose up -d db` the database needs the compose credentials: set
`DATABASE_URL=postgresql://risklens:risklens@localhost:5432/risklens` in `backend/.env`.

Open http://localhost:5173 and click **Use the demo portfolio**. The first upload fetches prices from
Yahoo Finance and takes a few seconds. API docs are at http://localhost:8000/docs.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/portfolios` | Upload a CSV (multipart: `file`, `name`, optional `benchmark`) |
| GET | `/api/portfolios` | List portfolios |
| GET | `/api/portfolios/{id}` | Holdings with current values |
| DELETE | `/api/portfolios/{id}` | Delete |
| GET | `/api/portfolios/{id}/risk` | All metrics. Query: `confidence`, `horizon`, `lookback` |
| POST | `/api/portfolios/{id}/scenario` | Stress test: `market_shock`, `custom_shocks` or `historical_replay` |
| GET | `/api/portfolios/{id}/backtest` | VaR validation. Query: `window` |
| GET | `/api/scenario-events` | Named historical events for the replay |
| GET | `/api/health` | Liveness plus a database check |

Errors always look like `{"code": "...", "message": "...", "details": ...}`. Every response carries
`X-Request-ID`.

## Project layout

```
backend/app/core       pure maths: returns, metrics, var, attribution, scenarios, backtest
backend/app/services   data cache, CSV import, portfolio, risk, scenario and backtest services
backend/app/api        thin FastAPI routers, error handlers, request-id middleware
backend/app/schemas    Pydantic request and response models
backend/alembic        migrations
backend/tests          unit/ (hand calculation, edge cases, properties) and api/ (TestClient)
frontend/src           pages, charts, components, typed API client, design tokens
benchmarks/            timing scripts
docs/                  ARCHITECTURE, METHODOLOGY, DECISIONS, INTERVIEW_NOTES, hand_calculation
```

## Tests and quality

```bash
cd backend  && .venv/bin/pytest --cov=app/core --cov=app/services   # 188 tests
cd backend  && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy
cd frontend && npm run lint && npm run typecheck && npm test && npm run build   # 33 tests
```

Tests never use the network: prices come from a seeded synthetic fixture (`backend/tests/fixtures`) behind
a fake `PriceProvider`. [docs/hand_calculation.md](docs/hand_calculation.md) works a two-stock example by
hand and a test reproduces every number. Coverage of `core/` and `services/` together is 99%, and CI
requires 85%. GitHub Actions (`.github/workflows/ci.yml`) runs ruff, mypy, pytest with the coverage gate,
the Alembic migrations on a PostgreSQL service, and the frontend lint, type check, tests and build.

## Benchmarks

Measured on an Apple Silicon Mac (macOS 26.5, Python 3.12.16, NumPy 2.5.4, pandas 3.1.0). Run them again
on your own machine; these are the output of the scripts in `benchmarks/`, unedited.

**Covariance of 756 daily returns** (`benchmarks/covariance_bench.py`): a loop written the way the formula
reads, against NumPy and pandas. The three agree to numerical precision before any timing is taken.

```
assets   python loop   numpy.cov  DataFrame.cov  loop / numpy
     5        0.34ms     0.020ms        0.025ms           17x
    10        1.18ms     0.020ms        0.031ms           58x
    25        6.88ms     0.027ms        0.051ms          254x
    50       27.14ms     0.048ms        0.055ms          562x
   100      109.95ms     0.081ms        0.097ms         1360x
```

**Price cache** (`benchmarks/cache_bench.py`): nine tickers, three years, from Yahoo Finance against the
local PostgreSQL cache. The cold figure is a single run and depends on the network.

```
9 tickers, 6831 price rows (2023-10-23 to today)

cold, Yahoo Finance + inserts :    3.108 s
warm, Postgres cache (median of 30):     17.6 ms
warm, fastest                 :     14.5 ms
speed-up                      :      177x
```

**Rolling backtest** (`benchmarks/backtest_bench.py`): about 530 test days at 95%, seeded synthetic returns.
Historical and parametric are vectorised; Monte Carlo re-estimates the covariance and simulates 10,000
paths every day.

```
assets   historical   parametric   monte carlo
     8        0.4ms        0.4ms        99.7ms
    25        0.3ms        0.4ms       154.7ms
    50        0.3ms        0.4ms       230.2ms
```

## Deployment

The repository is set up for Render (API and PostgreSQL) and Vercel (frontend). **It has not been
deployed yet**: that needs your own Render and Vercel accounts, so there are no live links here. The
steps:

1. Push the repository to GitHub.
2. **Render:** New, then Blueprint, and pick the repository. `render.yaml` creates the web service
   (built from `backend/Dockerfile`) and a PostgreSQL database and wires `DATABASE_URL`. The container
   runs `alembic upgrade head` before it starts. Health check path: `/api/health`.
3. **Vercel:** Add New Project, pick the repository, set **Root Directory** to `frontend`, and add the
   environment variable `VITE_API_URL` with the Render service URL (for example
   `https://risklens-api.onrender.com`, no trailing slash). Deploy.
4. Back on Render, set `CORS_ORIGINS` on the web service to the exact Vercel origin (for example
   `https://risklens.vercel.app`) and redeploy. Until then the browser blocks the frontend's requests.
5. Check `https://<your-api>/api/health`, then open the Vercel URL and click **Use the demo portfolio**.

A service on a free plan sleeps when idle, so the first request after a quiet spell can take up to a
minute; the interface says so while it waits. Check each provider's current free-tier terms. The demo
works from an empty database: it uploads the sample file, and the upload fetches and caches the prices.

## Limitations

- **Parametric and Monte Carlo VaR assume normal returns.** Fat tails make the 99% figure too small. The
  Monte Carlo here is normal, so with constant weights it converges to the parametric answer.
- **Historical VaR depends on its window.** A calm year says little about a crash.
- **Correlations rise in sell-offs,** so diversification measured in calm markets is weakest when it
  matters. Historical replay is the check against that.
- **VaR ignores how bad losses beyond it are,** which is why CVaR is shown. CVaR over a few hundred days
  is itself noisy.
- **Weights are constant** over the history: it is what today's portfolio would have done.
- **The market shock is single-factor,** with fixed betas.
- **One currency per portfolio.** Mixed portfolios are rejected; FX risk is not modelled.
- **Prices come from an unofficial Yahoo Finance library (yfinance).** It can be slow, rate limited or
  wrong for a ticker. It sits behind a small interface so it can be replaced.
- **The Kupiec test has limited power** (at 99% over two years only about five breaches are expected) and
  does not detect clustered breaches.
- **No authentication.** Anyone who can reach the API can list and delete every portfolio. Fine for a
  portfolio project, not for real use.
- **Not tested here:** the Docker image and `docker-compose.yml` were written but not built on the
  machine this was developed on, and the GitHub Actions workflow has not run on GitHub. Each CI step
  was run locally.

## More

[Architecture](docs/ARCHITECTURE.md) · [Methodology](docs/METHODOLOGY.md) ·
[Decisions](docs/DECISIONS.md) · [Interview notes](docs/INTERVIEW_NOTES.md)
