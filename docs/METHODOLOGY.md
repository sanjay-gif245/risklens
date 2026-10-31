# Methodology

Every formula the application uses, with the intuition behind it and the situations in which it
fails. The same material is shown in the Methodology page of the app. Code references point to the
function that implements each formula. All of it lives in `backend/app/core`, which has no web or
database imports, so each function can be read and tested on its own.

Conventions used throughout: VaR and CVaR are positive numbers (a loss of 2% is 0.02). Returns are
daily log returns. A year is 252 trading days.

## 1. Data

**Prices.** Daily adjusted close from Yahoo Finance, three years. Adjusted close folds in splits and
dividends so they do not show up as false returns.

**Log returns.** `r(t) = ln(P(t) / P(t-1))` (`returns.log_returns`). They add across time, treat up
and down moves symmetrically, and are what the covariance and the simulation assume. For one day
they differ from simple returns by a rounding error.

**Alignment.** Tickers have different holidays. `returns.align_prices` forward-fills a gap of up to
three days with the last price, then drops any date on which some ticker is still missing. The
sample is therefore the period in which every holding and the benchmark have a price.

*Failure mode:* a forward-filled day has a return of exactly zero for that ticker, which slightly
understates its volatility and correlations. Three days is a deliberate cap.

**Minimum history.** A holding with fewer than 252 trading days is excluded and reported
(`returns.split_by_history`). A covariance estimated from under a year is dominated by noise.

## 2. Weights and the portfolio return

`w(i) = quantity(i) x last price(i) / total value`. The portfolio return on a past day is
`sum_i w(i) r(i, t)` (`returns.portfolio_returns`).

*Assumption:* weights are constant over the whole history, so the series answers "what would
today's portfolio have done". It ignores that real weights drift and that you may have held
different positions then.

## 3. Volatility, return, Sharpe

```
sigma_p            = sqrt( w' S w )           S = sample covariance matrix (n - 1 divisor)
annual volatility  = sigma_p x sqrt(252)
annual return      = mean daily return x 252
Sharpe             = (annual return - risk-free rate) / annual volatility
```

`metrics.portfolio_volatility` computes the first line from the covariance matrix, which shows where
diversification comes from: the off-diagonal terms. `metrics.annualized_volatility` computes the same
number from the portfolio return series; the two agree.

*Failure modes:* scaling by sqrt(252) assumes independent days; volatility clustering breaks this.
The Sharpe ratio is undefined at zero volatility (returned as null). The risk-free rate is a
configured assumption (`config.py`), not live data.

## 4. Drawdown, beta, correlation

```
value(t)            = exp( cumulative sum of daily log returns )     starts at 1.0
drawdown(t)         = value(t) / running peak - 1                    zero or negative
max drawdown        = - min drawdown, with the dates of its peak and trough
beta                = cov(portfolio, benchmark) / var(benchmark)
correlation         = cov(portfolio, benchmark) / ( sd(portfolio) x sd(benchmark) )
```

The running peak starts at the initial value 1.0, so a fall from the first day counts. Beta says how
many percent the portfolio moves per percent of benchmark move; correlation says how tightly it
follows regardless of size.

*Failure mode:* beta is a regression on one window and one benchmark. It is not stable through a
crash.

## 5. Value at risk

VaR answers: what loss should be exceeded on only `1 - c` of days (5% at 95% confidence)?

**Historical** (`var.historical_var`). `VaR = - percentile(returns, 100 (1 - c))`, with linear
interpolation between order statistics. No distribution is assumed. *Fails when* the window held no
stress: a quiet year gives a small VaR. It also cannot see a loss larger than any in the sample.

**Parametric** (`var.parametric_var_from_moments`). `VaR = - (mean + z sigma)` with
`z = Phi^-1(1 - c)` from `scipy.stats.norm`. *Fails when* returns have fat tails, which they do:
the normal assigns too little probability to extreme moves, so 99% VaR is usually too small.

**Monte Carlo** (`var.simulate_portfolio_returns`). Draw 10,000 vectors `z` of independent standard
normals (fixed seed), set `L` as the Cholesky factor of the covariance (`L L' = S`), and form
`asset returns = mean + L z` and `portfolio return = w' x asset returns`. VaR is the historical
percentile of the simulated returns. Perfectly correlated assets give a singular covariance matrix,
which plain Cholesky rejects, so a tiny diagonal jitter scaled to the matrix is added (up to 1e-8 of
the average variance).

*Important:* with constant weights and normal draws, this converges to the parametric answer; the
two differ only by sampling noise. It is a cross-check and an extension point (fat-tailed draws, or
non-linear positions such as options), not a separate model of the world.

**Horizon.** An h-day VaR is the 1-day VaR times sqrt(h). *Fails when* returns are autocorrelated or
volatility clusters, in which case multi-day losses are larger.

## 6. Expected shortfall (CVaR)

`CVaR = - mean( returns at or below the VaR cut-off )` (`var.historical_cvar`), scaled by sqrt(h).

VaR marks where the tail starts and says nothing about how deep it goes. CVaR is the average loss
given that you are in the tail, so it is never smaller than VaR. It is reported for the historical
and Monte Carlo estimators. *Fails* in that a 5% tail of three years is about 38 days; the average of
so few observations is itself uncertain.

## 7. Risk contribution

```
component(i) = w(i) x (S w)(i) / sigma_p              sum over i of component(i) = sigma_p
```

(`attribution.risk_contributions`). This is Euler's decomposition of a homogeneous function: the
contributions add up exactly to portfolio volatility (asserted in the tests on random data), so
each holding's share of risk can be set beside its share of capital. A volatile stock with a small
weight can carry a large share; a defensive one can carry almost none.

*Failure mode:* contributions are marginal and local to the current weights. They do not say what
happens if you sell the position, because the other contributions change too.

## 8. Scenarios

**Market shock** (`scenarios.market_shock`). The benchmark moves by `x`; holding `i` moves by
`beta(i) x x`. The portfolio move equals portfolio beta times `x`, because beta is linear in the
weights. *Single-factor:* it ignores everything specific to a stock and assumes betas hold in a
crash, which they usually do not.

**Custom shocks** (`scenarios.custom_shocks`). A percentage move per named ticker, zero elsewhere.

**Historical replay** (`scenarios.historical_replay`). The return of each holding is its last price
over its first price in the window, minus one, applied to today's market value: a buy-and-hold of
today's portfolio through the episode. A holding whose first price falls more than four days after
the window start, or whose last price falls more than four days before its end, did not trade
through it. It is marked not covered and left out of the totals. The result is reported for the
covered share only, and the share is stated.

## 9. Backtest and the Kupiec test

**Procedure** (`backtest.rolling_var`, `backtest.backtest_var`). For each day after the first
`window` days (default 250), estimate the 1-day VaR from the previous `window` days only, then
compare it with that day's realized portfolio return. A breach is a day with `return < - VaR`. The
test confirms by construction that the day's own return never enters its own VaR.

**Kupiec proportion-of-failures test** (`backtest.kupiec_pof`). Null hypothesis: the true breach
probability is `p = 1 - c`. With `x` breaches in `N` days:

```
LR = -2 ln[ (1-p)^(N-x) p^x ]  +  2 ln[ (1 - x/N)^(N-x) (x/N)^x ]
LR ~ chi-square(1) under the null;   p-value = P(chi-square(1) >= LR)
```

The first term is the log-likelihood if the model is right, the second the best possible fit to
what was observed. A large `LR` means the observed rate is too far from `p` for luck. At the 5% level
the model is rejected when the p-value is below 0.05. `x = 0` and `x = N` are handled by treating
`0 ln 0` as 0. `docs/hand_calculation.md` works one case by hand and a test reproduces it
(N = 100, x = 2, p = 0.05 gives LR = 2.4286, p-value 0.1191).

**Reading a result.** *Rejected with too many breaches:* the model understates risk. *Rejected with
too few:* the model is overly cautious. *Accepted:* the data do not contradict the model.

*Failure modes:* the test has low power. At 99% over 500 days only about five breaches are expected,
and a model that is modestly wrong passes. The API warns when fewer than five breaches are expected.
The test also ignores clustering: a model whose breaches all arrive in one week can pass. The
independence test of Christoffersen addresses that and is not implemented.

## 10. Limitations in one place

1. Parametric and Monte Carlo VaR assume normal returns; fat tails make 99% VaR too small.
2. Historical VaR depends entirely on its window.
3. Correlations rise toward 1 in a sell-off, so the diversification measured in calm periods is
   least reliable when it matters.
4. VaR says nothing about the size of losses beyond it; CVaR partly answers that and is itself noisy.
5. Weights are held constant over the history.
6. The market shock uses one factor and fixed betas.
7. Mixed-currency portfolios are rejected; FX risk is not modelled.
8. Prices come from an unofficial Yahoo Finance library that can be slow, rate limited or wrong for
   individual tickers.
9. Square-root-of-time scaling of volatility and VaR assumes independent days.
10. The Kupiec test has limited power and ignores breach clustering.
