# Decisions

Each entry records a choice the brief left open, or one that is not obvious from the code, and the
reason for it. Where a decision limits what the product can do, the limit is stated.

## Finance

**Log returns, combined linearly across assets.** The portfolio return on a day is the weighted
sum of the holdings' log returns. Strictly, log returns do not add across assets (simple returns
do). For daily moves the gap is far below the estimation error of the covariance matrix, and
the benefit is one formula used everywhere. (`core/returns.py`)

**Weights are today's market values and stay constant.** The history is "what today's portfolio
would have done", which is the question risk answers. Reconstructing past weights from buy
dates and prices would answer a different question (performance attribution) and needs dates the
CSV does not have.

**Square-root-of-time scaling for every method, including historical.** An h-day VaR is the 1-day
VaR times sqrt(h). Scaling the whole figure is one rule that is easy to state. A more careful
parametric version scales the mean by h and the volatility by sqrt(h); with daily means near zero
the difference is negligible. Historical VaR over a real h-day window would need overlapping
returns and gives a noisy estimate.

**Monte Carlo is a multivariate normal.** The brief asks for a Cholesky simulation. With constant
weights, a normal simulation converges to the parametric VaR, so the two differ only by sampling
noise. I kept it because it cross-checks the parametric formula and because it is the place where a
fat-tailed or non-linear model would plug in. It is not presented as an independent opinion, and the
methodology page says so. (`core/var.py`, `simulate_portfolio_returns`)

**The backtest reuses one set of random draws.** Inside the rolling Monte Carlo backtest the same
10,000 standard normals are used every day (common random numbers). Day-to-day movement in the VaR
then comes from the data, not from simulation noise, and the loop stays fast. The seed is fixed.

**Kupiec test, two-sided, 5% level.** A model that breaches far less than promised is rejected as
overly cautious, because over-conservative capital has a cost. The test says nothing about whether
breaches cluster; that needs Christoffersen's independence test, which is not implemented.

**A breach is a strict inequality.** A day counts when the return is below minus the VaR.

**Backtest window of 250 days, adjustable between 60 and 750.** It is the conventional "one trading
year". A shorter window reacts faster and is noisier.

**The risk-free rate is configuration, not data.** Defaults are 4% for USD and 6.5% for INR, set in
`config.py` and overridable by environment variable. They are assumptions and are shown on screen
next to the Sharpe ratio. Update them before relying on the Sharpe figure.

**Named scenario windows.** COVID crash (19 Feb to 23 Mar 2020), the 2008 crisis (12 Sep 2008 to 9
Mar 2009) and the 2022 rate shock (3 Jan to 12 Oct 2022). The dates are the S&P 500 high and low
of each episode; for Indian portfolios they are still the right episodes, though not the exact
local peaks and troughs. Custom dates are also accepted.

## Data

**Duplicate tickers are merged, not rejected.** Quantities add and the buy price becomes the
quantity-weighted average, which is how a broker statement with several lots would collapse. The
upload response includes a notice so the merge is visible. (`services/csv_import.py`)

**More than 50 holdings counts distinct tickers**, after merging.

**Currency comes from the ticker suffix.** `.NS` and `.BO` are INR, everything else USD. Mixed
portfolios are rejected with a message naming the tickers on each side. A real fix needs FX history
and an FX risk factor, which is a different model. Documented as a limitation.

**Benchmark defaults by currency** (^NSEI for INR, ^GSPC otherwise) and can be overridden. The
benchmark needs at least 252 days of history like any holding.

**Alignment: forward-fill at most three days, then drop incomplete dates.** Three days covers a long
weekend plus a holiday. The result is an inner join in practice: the sample starts when the youngest
holding or the benchmark starts. When that shortens the sample by more than 10%, a warning names the
ticker responsible. (`core/returns.py`, `services/portfolio_service.py`)

**Holdings with under 252 trading days are excluded, never silently.** The exclusion is listed in the
upload response, in a banner on the overview page, and in the risk and scenario responses.

**The price cache remembers bounds, not individual days.** For each ticker it knows the first and
last cached date and fetches only what lies outside. A missing weekday inside the bounds is almost
always a holiday, and chasing it would cost a network call on every request. Known cost: a stock
listed after the requested start is looked up again on every request (the head range is always
"missing"), and a historical replay that reaches back before the cache pulls the whole gap, not just
the window. Both are correct, and both are wasteful in a way a coverage table would fix.
(`services/data_service.py`)

## Engineering

**Services return Pydantic response models directly.** The brief's layering is routers, services,
core. A separate DTO layer between services and routers would add a mapping step with no behavior in
it, so the services build the response schemas themselves.

**Dialect-neutral database types.** Tables use SQLAlchemy `Uuid` and plain `Float` so the same models
run on SQLite in the tests and PostgreSQL in production. Tests are fast and offline. CI also runs
the Alembic migrations on a real PostgreSQL service so a dialect difference cannot hide.

**`PriceProvider` is an interface.** yfinance is an unofficial scraper. The data service depends on a
one-method protocol, so swapping the source, or faking it in tests, touches one class. The yfinance
implementation retries three times with exponential backoff (1 s, then 2 s) and converts a final
failure into a 502 with a readable message.

**One error envelope.** Every failure leaves as `{code, message, details}`: application errors,
validation errors, unknown routes and unexpected exceptions. Unexpected errors return the request id
and never the exception text.

**Migrations run when the container starts.** The Dockerfile runs `alembic upgrade head` before
uvicorn. They are idempotent, so a restart with no new revision does nothing. The alternative, a
separate release step, is better at scale (no two instances racing) and worse for a one-instance demo.

**Tests use synthetic prices.** `tests/fixtures/synthetic_prices.csv` is seeded random data, so the
suite is offline and deterministic. It is labelled synthetic in `tests/fixtures/README.md`. Nothing
in the product is synthetic: the live app only ever shows prices fetched from Yahoo Finance.

**No authentication.** This is a portfolio project. Anyone who can reach the API can list, read and
delete every portfolio. Real use needs accounts and per-user ownership. It is listed under
limitations in the README.

## Frontend

**No CSS framework and no component kit.** One token file (`theme/theme.css`) and one stylesheet
(`theme/app.css`). The palette and typography are the product's identity; a kit would pull them
toward its defaults.

**Recharts 2.** Version 3 exists and 2.x no longer receives features. Version 2 is stable with React
18 and the custom tooltips used here; moving to 3 is a contained change, since the chart code is
isolated in `src/charts/`. Chart colours are literal values in `lib/chartTheme.ts` because Recharts
needs them in JavaScript; they mirror the CSS tokens.

**API types are written by hand** in `api/types.ts` and mirror `backend/app/schemas`. Generating them
from the OpenAPI document would remove the duplication; at six endpoints the generator costs more
than it saves.

**Fonts are self-hosted** through `@fontsource` packages, so the page makes no request to a font CDN.

**Motion is limited to a one-time number count-up and a loading shimmer**, and both stop when the
viewer asks for reduced motion.

**Every chart has a text equivalent.** Each chart sits in a figure whose `aria-label` and visible
caption state the finding in words, and the correlation matrix is a real table.
