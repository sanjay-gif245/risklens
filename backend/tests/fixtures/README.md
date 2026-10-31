# Test fixtures

`synthetic_prices.csv` is **synthetic**: seeded random prices, not market data.
It exists so tests run offline and always give the same answer.

- 780 business days, 2021-01-04 to 2023-12-29, columns: `^GSPC`, `AAA`, `BBB`,
  `CCC`, `NEWCO` (US-style) and `^NSEI`, `RELI.NS`, `TCSX.NS` (Indian-style).
- Each stock follows a one-factor model: daily log return = beta x market
  return + idiosyncratic noise, from `numpy.random.default_rng(2024)`. Betas are
  1.2 (AAA), 0.8 (BBB), 1.0 (CCC), 1.5 (NEWCO), 1.1 (RELI.NS), 0.7 (TCSX.NS).
- A stress episode (twenty days of roughly -1.2% market returns) sits at business
  days 600 to 619, so scenario and backtest tests have a crash to react to.
- `NEWCO` only has prices for the last 120 days, to test the short-history rule.
- `BBB` is missing two consecutive days, to test the holiday gap fill.
