// Written for a reader who knows some finance. The same content lives in docs/METHODOLOGY.md.

export function MethodologyPage() {
  return (
    <article className="prose">
      <div className="label">Methodology</div>
      <h1 style={{ marginTop: 12 }}>How the numbers are calculated</h1>
      <p style={{ marginTop: 20 }}>
        Every figure in RiskLens comes from the formulas below, applied to three years of daily
        prices. Each section states what the formula assumes and when it stops being reliable. The
        limitations at the end are not fine print: they are the reason the backtest exists.
      </p>

      <h2>Data and returns</h2>
      <p>
        Prices are daily adjusted closes, so splits and dividends do not appear as false moves.
        Daily <strong>log returns</strong> are used throughout:
      </p>
      <pre>
        <code>r(t) = ln( P(t) / P(t-1) )</code>
      </pre>
      <p>
        Log returns add across days and treat gains and losses symmetrically, which is what the
        covariance matrix and the normal model assume. For one day the difference from a simple
        return is tiny.
      </p>
      <p>
        Holidays differ between tickers. A gap of up to three days is filled with the last price,
        then any incomplete day is dropped, so the sample is the period in which every holding and
        the benchmark have a price. A holding with fewer than 252 trading days of history is left
        out and reported, because a covariance estimated from less than a year is unreliable.
      </p>

      <h2>Weights</h2>
      <p>
        The weight of a holding is its current market value (quantity times latest price) divided by
        the total. These weights are held <strong>constant</strong> over the whole history, so the
        portfolio return on a past day is what today's portfolio would have earned. That is the
        right question for forward-looking risk, and it ignores that real weights drift.
      </p>

      <h2>Volatility, return and Sharpe ratio</h2>
      <pre>
        <code>{`sigma_p = sqrt( w' S w )               daily, S = sample covariance matrix
annual volatility = sigma_p x sqrt(252)
annual return     = mean daily return x 252
Sharpe            = (annual return - risk-free rate) / annual volatility`}</code>
      </pre>
      <p>
        The square-root-of-time scaling assumes returns are independent from day to day. The
        risk-free rate is a configured assumption, not live data: 4% for USD portfolios and 6.5% for
        INR portfolios by default.
      </p>

      <h2>Drawdown, beta and correlation</h2>
      <pre>
        <code>{`drawdown(t) = value(t) / running peak - 1
beta        = cov(portfolio, benchmark) / var(benchmark)
correlation = cov(portfolio, benchmark) / (sd(portfolio) x sd(benchmark))`}</code>
      </pre>
      <p>
        Maximum drawdown is the deepest drawdown, reported with the dates of its peak and trough.
        Beta measures sensitivity to the benchmark; correlation measures how closely the two move
        together, whatever their sizes.
      </p>

      <h2>Value at risk</h2>
      <p>
        VaR answers one question: what is the loss that should be exceeded only on 5% (or 1%) of
        days? Losses are shown as positive numbers. Three estimators are computed.
      </p>
      <h3>Historical</h3>
      <pre>
        <code>VaR = - percentile( past portfolio returns, 100 x (1 - confidence) )</code>
      </pre>
      <p>
        No distribution is assumed, so fat tails show up if they occurred in the window. The cost:
        it knows only about losses that happened in the window, and a quiet window gives a
        reassuring answer.
      </p>
      <h3>Parametric</h3>
      <pre>
        <code>VaR = - ( mean + z x sigma ), z = Phi^-1(1 - confidence)</code>
      </pre>
      <p>
        Assumes normal returns. Real returns have fatter tails, so at 99% this tends to understate
        the loss.
      </p>
      <h3>Monte Carlo</h3>
      <p>
        Draw 10,000 vectors of independent standard normals z, correlate them with the Cholesky
        factor L of the covariance matrix (L L' = S), and add the mean:
      </p>
      <pre>
        <code>{`asset returns = mean + L z
portfolio return = w' x asset returns
VaR = historical VaR of the 10,000 simulated portfolio returns`}</code>
      </pre>
      <p>
        The random seed is fixed so results are reproducible. With constant weights and normal
        draws, this converges to the parametric answer; the two differ only by sampling noise. Its
        value is as a cross-check and as the place to plug in fat-tailed draws or non-linear
        positions, which this version does not do.
      </p>
      <h3>Horizon</h3>
      <p>
        An h-day VaR is the 1-day VaR times the square root of h. Like the volatility scaling, this
        assumes independent days and understates risk when losses cluster.
      </p>

      <h2>Expected shortfall (CVaR)</h2>
      <pre>
        <code>CVaR = - average of returns at or beyond the VaR cut-off</code>
      </pre>
      <p>
        VaR says where the tail begins and nothing about how bad it is. CVaR is the average loss
        given that you are in the tail, so it is always at least the VaR. It is shown for the
        historical and Monte Carlo estimators.
      </p>

      <h2>Risk contribution</h2>
      <pre>
        <code>{`component(i) = w(i) x (S w)(i) / sigma_p
sum of components = sigma_p`}</code>
      </pre>
      <p>
        The contributions add up exactly to the portfolio volatility, so each holding's share of
        risk can be set beside its share of capital. A volatile position with a small weight can
        carry a large share of the risk; a defensive one can carry very little.
      </p>

      <h2>Scenarios</h2>
      <p>
        <strong>Market shock.</strong> The benchmark moves by x; each holding moves by its own beta
        times x. This is a single-factor model: it ignores everything specific to a stock and
        assumes betas hold in a crash.
      </p>
      <p>
        <strong>Custom shocks.</strong> You choose the percentage move for any holding. The rest are
        unchanged.
      </p>
      <p>
        <strong>Historical replay.</strong> The actual price move of each holding over a past
        window, applied to today's market values. Holdings that did not trade at the start or end of
        the window are reported as not covered, and the result covers only the others.
      </p>

      <h2>Backtest and the Kupiec test</h2>
      <p>
        For every day after the first 250, VaR is estimated using only the previous 250 days and
        compared with that day's actual return. A day on which the loss exceeded the VaR is a{' '}
        <strong>breach</strong>. A 95% model should breach on about 5% of days.
      </p>
      <p>
        The Kupiec proportion-of-failures test asks whether the observed breach count is plausible
        for the promised rate p = 1 - confidence. With x breaches in N days:
      </p>
      <pre>
        <code>{`LR = -2 ln[ (1-p)^(N-x) p^x ] + 2 ln[ (1-x/N)^(N-x) (x/N)^x ]
LR ~ chi-square with 1 degree of freedom under the null`}</code>
      </pre>
      <p>
        A p-value below 0.05 rejects the model. The test is two-sided: too few breaches is also a
        failure, because it means the model is overly cautious. It also has limited power: with 500
        test days a 99% model is expected to breach only about five times, and several outcomes look
        equally plausible. An accepted model has survived the test; it has not been proved right.
      </p>

      <h2>Limitations</h2>
      <ul>
        <li>
          <strong>Normality.</strong> Parametric and Monte Carlo VaR assume normal returns. Fat
          tails make the 99% figure too small.
        </li>
        <li>
          <strong>Window dependence.</strong> Historical VaR is only as good as the window. A calm
          year says nothing about a crash.
        </li>
        <li>
          <strong>Correlations rise in crashes.</strong> Diversification measured in calm markets
          shrinks when it matters. The correlation matrix describes the past window, not a sell-off.
        </li>
        <li>
          <strong>VaR ignores severity.</strong> It does not say how bad a loss beyond the cut-off
          is. That is what CVaR adds.
        </li>
        <li>
          <strong>Constant weights.</strong> The portfolio is treated as if held unchanged over the
          history.
        </li>
        <li>
          <strong>Single-factor scenarios.</strong> The market shock uses one factor and fixed
          betas.
        </li>
        <li>
          <strong>One currency.</strong> Mixed-currency portfolios are rejected, because exchange
          rates would add a risk this model does not measure.
        </li>
        <li>
          <strong>Data source.</strong> Prices come from Yahoo Finance through an unofficial
          library. It can be slow, rate limited or wrong for individual tickers.
        </li>
      </ul>
    </article>
  )
}
