# Interview notes

Written to be read aloud, in my own voice. Nothing here needs more than the code and
`METHODOLOGY.md`. If a question goes deeper than my answer, I say what I know and where I would look.

## The 60-second pitch

"RiskLens takes a CSV of holdings, fetches three years of prices, and tells you how risky the
portfolio is the way a risk desk would: volatility, value at risk and expected shortfall, and which
holdings the risk actually comes from. It stress tests the portfolio, for example by replaying the
COVID crash on today's holdings. The part I'm proudest of is that it also checks itself. It
runs a rolling backtest, estimating VaR each day using only the days before it, counts how often the
real loss was bigger, and runs a Kupiec test to say whether the model is statistically acceptable. So
the output isn't just a number, it's a number plus evidence on whether to trust it. The maths is in a
pure Python package that I tested against a calculation I did by hand, and the whole thing has CI, a
Postgres price cache and a React front end."

## The 3-minute walkthrough

**Start with the question.** "A portfolio manager asks: how much could I lose on a bad day, and
what drives that?"

**The data.** "You upload ticker, quantity and buy price. I validate every row and report all
problems at once with row numbers. Then I fetch three years of adjusted closes through a
`PriceProvider` interface, because yfinance is unofficial and flaky, so I retry with backoff and turn
failures into clear 502s. Prices are cached in Postgres per ticker and date, and I only fetch what
is missing. A cold load of nine tickers took about three seconds and a warm one about eighteen
milliseconds on my laptop."

**The maths.** "Everything is in `core/`, pure functions over pandas and NumPy with no web or
database imports. I use daily log returns and weights from current market values, held constant.
Volatility is the square root of w-transpose S w. VaR three ways: historical percentile, parametric
with the normal, and Monte Carlo through a Cholesky factor of the covariance. CVaR is the average loss
beyond VaR. For risk contribution I use Euler's decomposition, and a test asserts the
contributions add up to the portfolio volatility."

**Scenarios.** "A market shock using beta, custom shocks, and historical replay: take what each holding
actually did between two dates and apply it to today's values. If a stock didn't exist then, I flag it
and report the covered share instead of guessing."

**The backtest.** "For each day I estimate VaR from the previous 250 days only, and compare it to
that day's return. A breach is a loss bigger than the VaR. A 95% model should breach about 5% of the
time, and the Kupiec likelihood-ratio test gives a p-value for whether the observed rate is
consistent with that. A test checks that today's return can't leak into today's VaR."

**Quality.** "I reproduce a two-stock hand calculation exactly in a test, test properties like VaR 99
being at least VaR 95, and run API tests with a fake price provider so nothing touches the network.
CI runs lint, types, tests with an 85% gate and a real Postgres migration. Core and services are at
99% coverage."

**Close with the honest part.** "It assumes constant weights, one currency per portfolio, and the
Monte Carlo is a normal simulation that converges to parametric VaR, so I describe it as a
cross-check, not a separate opinion. There's no authentication. I'd fix those first."

## Key design decisions and why

| Decision | Reason |
|---|---|
| `core/` has no web or DB imports | Every formula is testable against a hand calculation, and explainable in isolation |
| Log returns | They add over time and are symmetric, which covariance and the normal model expect |
| Weights from current market value, constant | Risk is a forward-looking question about today's portfolio |
| Price cache keeps first and last date per ticker | One cheap query decides what to fetch, no per-day bookkeeping, and holidays do not cause repeat fetches |
| `PriceProvider` interface | yfinance can break or be replaced; the rest of the code and the tests don't care |
| Services build the response models | A separate mapping layer would have no behaviour in it |
| One error envelope for everything | The front end handles one shape, including row-level CSV problems |
| Synthetic fixtures in tests | Offline, deterministic, and labelled as synthetic |
| No UI kit, one token file | The palette and type are the identity of the product |

## What I'd do differently, and how I'd scale to 10,000 portfolios

**Differently.**
- Add authentication and per-user ownership. Today anyone who reaches the API can list every portfolio.
- Make the Monte Carlo earn its place: draw from a multivariate Student-t, or do filtered historical
  simulation, so it can disagree with parametric VaR where it matters (the tails).
- Add Christoffersen's independence test beside Kupiec, because breaches that cluster in a crisis are
  the failure Kupiec cannot see.
- Replace the single-factor market shock with a few factors, or with the replay of a stressed
  covariance matrix.
- Record price coverage in a table, so young stocks and old replays stop causing repeat fetches.

**To 10,000 portfolios.** The prices are shared, so the data does not grow with portfolios: the number
of tickers does. Compute is the part that scales. A risk request is tens of milliseconds and a
backtest a few hundred, almost all Monte Carlo, so:
1. Take Yahoo out of the request path. A scheduled job loads closing prices for the whole ticker
   universe after market close, ideally from a licensed vendor.
2. Compute analyses in a queue with workers, store results keyed by portfolio, parameters and price
   date, and serve from the store. Prices change once a day, so a result is valid all day.
3. Make the backtest cheaper: simulate once per day for both confidence levels, and share random
   draws across portfolios.
4. Read replicas for the portfolio reads, partitioning of `prices` by ticker or date if the table
   grows, connection pooling in front of Postgres.
5. Stateless API instances behind a load balancer, with migrations as a release step rather than on
   container start so two instances never race.

## The 20 questions I expect

**1. What is VaR, in one sentence?**
The loss you'd expect to exceed on only 5% of days (at 95%), so a 1-day 95% VaR of 2% means that on
19 days out of 20 you lose less than 2%. It's a threshold, not a worst case. In the code it's
`core/var.py`, and losses are returned as positive numbers.

**2. You have three VaR methods. When does each one fail?**
Historical fails when the window was calm, because it can only repeat losses that happened. Parametric
fails when returns have fat tails, because the normal gives too little probability to extreme days,
especially at 99%. Monte Carlo in my version is normal, so it fails the same way as parametric. Its
value is as a cross-check and as the place to plug in fat-tailed draws.

**3. Why log returns?**
They add across time, they're symmetric for up and down moves, and the covariance and the simulation
assume that. One caveat I state in `DECISIONS.md`: log returns don't strictly add across assets, so
combining them with weights is an approximation, negligible for daily moves.

**4. Why multiply by the square root of 252, and by the square root of h for a multi-day VaR?**
If daily returns are independent, variance adds over time, so standard deviation grows with the square
root of time. It breaks when volatility clusters or returns are autocorrelated, and then it understates
multi-day risk. I use the same scaling for every method so there's one rule to state.

**5. What is CVaR and why report it?**
It's the average loss on the days that breach VaR. VaR tells you where the tail begins and nothing
about how deep it is; two portfolios can have the same VaR and very different tails. CVaR is always at
least VaR. I report it for historical and Monte Carlo and leave it off parametric because there it
just restates the normal assumption.

**6. What does risk contribution mean, and how is it computed?**
Each holding's share of portfolio volatility: `w_i x (S w)_i / sigma_p`. They sum exactly to the
portfolio volatility, which my test asserts on random data, so I can put each holding's share of risk
next to its share of capital. A volatile small position can carry a big share of risk, which is the
point of showing both.

**7. How do you read the backtest?**
For each day, I estimate VaR from the previous 250 days, then check whether the actual loss was bigger.
A bigger loss is a breach. A 95% model should breach about 5% of days. Too many breaches means the
model understates risk, too few means it's overly cautious. The chart shows the returns, the VaR
limit, and the breach days in red.

**8. What's the Kupiec test, and what's its null hypothesis?**
The null is that the true breach probability equals 1 minus the confidence level. The statistic
compares the likelihood of the observed breach count under that probability with the best possible fit
to the data, and it's chi-square with one degree of freedom under the null. A p-value under 0.05
rejects the model. It's two-sided. `core/backtest.py` has it, and I tested it against a case worked by
hand in `docs/hand_calculation.md`.

**9. Your backtest accepted the model. Does that mean the model is right?**
No. It means the data didn't contradict it. The test has low power, particularly at 99% over about 500
days, where only five breaches are expected. It also ignores clustering: breaches all in one week can
still pass. The page warns when fewer than five breaches are expected.

**10. Monte Carlo and parametric give nearly the same VaR. Why bother with Monte Carlo?**
Because with constant weights and normal draws they must agree, and that's useful: if they disagreed
by a lot I'd know I had a bug. It's also the extension point: change the draws to Student-t, or
simulate non-linear positions, and it becomes a genuinely different model. I say this on the
methodology page rather than present it as independent evidence.

**11. Why do correlations matter in a crash?**
In calm markets stocks partly offset each other, which is why the portfolio is less risky than its
parts. In a sell-off correlations tend toward 1, so that offset disappears just when you need it.
My correlation matrix and my volatility describe the window I measured, which is why I also show a
historical replay of an actual crash.

**12. What does the constant-weights assumption do to the results?**
It makes the history "what today's portfolio would have done". That's right for forward risk and wrong
as a record of performance. If you bought your biggest position last month, the past volatility I
report still uses that weight.

**13. How do you handle missing data and market holidays?**
`align_prices` forward-fills at most three days, then drops dates where any ticker is still missing, so
the sample is where everyone has a price. A filled day has a return of zero, which is why I cap it at
three. Holdings with under 252 days are excluded and reported in warnings, never silently.

**14. How does the cache work, and where does it break?**
For each ticker I store the first and last cached date. A request fetches only the range outside
those bounds. It doesn't chase single missing days because they're nearly always holidays. It breaks
down for a stock listed after the requested start, which is looked up again every time, and a replay
older than the cache pulls the whole gap. A coverage table would fix both.

**15. Why put yfinance behind an interface?**
It's an unofficial scraper that rate limits and changes. `PriceProvider` is one method, so swapping
the source means one class, and the tests use a fake that records calls. The real one retries three
times with exponential backoff and turns a final failure into a clear 502, not a 500.

**16. Walk me through the API design.**
Routers are thin: parse, call a service, return. Services do orchestration and call `core/`. Every
error leaves as `{code, message, details}`, including validation errors and unknown routes, and
status codes are meaningful: 422 for bad input, 404 missing, 413 file too large, 502 when the price
source is down. Every response has an `X-Request-ID` and every request gets one JSON log line.
CORS is read from an environment variable so production locks to the real frontend.

**17. How did you test the maths?**
Four ways. A hand calculation of two stocks over five days reproduced exactly in
`test_hand_calculation.py`. Edge cases: single stock, perfectly correlated stocks, zero variance,
extreme weights, short history. Properties that must always hold: contributions sum to volatility,
VaR 99 is at least VaR 95, CVaR is at least VaR. And a no-look-ahead test for the backtest.

**18. You test on SQLite but run Postgres. Isn't that risky?**
It's a trade-off I made on purpose: fast, offline tests. The models use dialect-neutral types, and
CI also runs the Alembic migrations on a real Postgres service, upgrade, downgrade, upgrade, so a
dialect difference in the schema can't hide. The cache queries are simple selects and inserts.

**19. Returns have fat tails. What would you do about it?**
Fit a Student-t, or use filtered historical simulation: scale historical returns by current volatility
from an EWMA or GARCH model, so a quiet window doesn't give a falsely small VaR. I'd check the change
with the same backtest, and at 99% I'd expect the parametric normal model to be rejected sooner than
the fat-tailed one.

**20. What's the weakest part of this project?**
No authentication, so portfolios are public to anyone who can reach the API. Then the single-factor
market shock, which assumes betas hold in a crash. Then the Monte Carlo being normal, so it adds no
information beyond parametric. And data: Yahoo through an unofficial library is fine for a demo and not
for production. I'd rather say that up front than have it found.
