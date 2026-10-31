import { useState } from 'react'
import { useRisk } from '../api/hooks'
import { ContributionChart } from '../charts/ContributionChart'
import { CorrelationHeatmap } from '../charts/CorrelationHeatmap'
import { DrawdownChart } from '../charts/DrawdownChart'
import { VarChart } from '../charts/VarChart'
import { PageHead } from '../components/PageHead'
import { Panel } from '../components/Panel'
import { Segmented } from '../components/Segmented'
import { ErrorState, PanelLoading, Warnings } from '../components/States'
import { formatDate, formatMethod, formatMoney, formatNumber, formatPercent } from '../lib/format'
import { usePortfolioContext } from './portfolioContext'

const CONFIDENCE = [
  { value: 0.95, label: '95%' },
  { value: 0.99, label: '99%' },
]
const HORIZON = [
  { value: 1, label: '1 day' },
  { value: 5, label: '5 days' },
  { value: 10, label: '10 days' },
]
const LOOKBACK = [
  { value: 0, label: 'All' },
  { value: 504, label: '2 years' },
  { value: 252, label: '1 year' },
  { value: 126, label: '6 months' },
]

export function RiskPage() {
  const { portfolio } = usePortfolioContext()
  const [confidence, setConfidence] = useState(0.95)
  const [horizon, setHorizon] = useState(1)
  const [lookback, setLookback] = useState(0)
  const risk = useRisk(portfolio.id, confidence, horizon, lookback === 0 ? null : lookback)
  const currency = portfolio.base_currency
  const data = risk.data

  return (
    <div className="stack">
      <PageHead section="Risk" portfolio={portfolio} />

      <div className="controls">
        <Segmented
          label="Confidence"
          options={CONFIDENCE}
          value={confidence}
          onChange={setConfidence}
        />
        <Segmented label="Horizon" options={HORIZON} value={horizon} onChange={setHorizon} />
        <Segmented
          label="History used"
          options={LOOKBACK}
          value={lookback}
          onChange={setLookback}
        />
      </div>

      {risk.isError && <ErrorState error={risk.error} onRetry={() => void risk.refetch()} />}
      {data && <Warnings items={data.warnings} />}

      <Panel
        label="Value at risk"
        title="Three ways to estimate the same loss"
        lede={
          data
            ? `Loss not expected to be exceeded on ${Math.round(confidence * 100)}% of ${horizon === 1 ? 'days' : `${horizon}-day periods`}, from ${data.observations} trading days (${formatDate(data.window_start)} to ${formatDate(data.window_end)}).`
            : undefined
        }
      >
        {risk.isPending && <PanelLoading height={340} />}
        {data && (
          <div className="grid-wide-narrow">
            <VarChart estimates={data.var} confidence={confidence} horizon={horizon} />
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Method</th>
                    <th className="num">VaR</th>
                    <th className="num">CVaR</th>
                  </tr>
                </thead>
                <tbody>
                  {data.var.map((e) => (
                    <tr key={e.method}>
                      <td>{formatMethod(e.method)}</td>
                      <td className="num">
                        {formatPercent(e.var_pct)}
                        <div className="muted">{formatMoney(e.var_amount, currency)}</div>
                      </td>
                      <td className="num">
                        {e.cvar_pct === null ? (
                          <span className="muted">&mdash;</span>
                        ) : (
                          <>
                            {formatPercent(e.cvar_pct)}
                            <div className="muted">{formatMoney(e.cvar_amount ?? 0, currency)}</div>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="muted" style={{ fontSize: 13, marginTop: 16 }}>
                Gold bars are VaR, oxblood bars are CVaR: the average loss on the days that breach
                VaR. Parametric CVaR is not shown; it would only restate the normal assumption.
              </p>
            </div>
          </div>
        )}
      </Panel>

      <div className="grid-2">
        <Panel
          label="Attribution"
          title="Where the risk comes from"
          lede="Each holding's share of portfolio volatility next to its share of capital."
        >
          {risk.isPending && <PanelLoading />}
          {data && <ContributionChart rows={data.contributions} />}
        </Panel>
        <Panel
          label="Diversification"
          title="Correlation of daily returns"
          lede={data ? `Between ${data.correlation.tickers.length} holdings.` : undefined}
        >
          {risk.isPending && <PanelLoading />}
          {data && (
            <CorrelationHeatmap
              tickers={data.correlation.tickers}
              matrix={data.correlation.matrix}
            />
          )}
        </Panel>
      </div>

      <Panel
        label="Drawdown"
        title="Falls from the previous peak"
        lede={
          data
            ? `Deepest fall ${formatPercent(data.summary.max_drawdown.depth)}, from ${formatDate(data.summary.max_drawdown.peak_date)} to ${formatDate(data.summary.max_drawdown.trough_date)}. Beta to ${data.benchmark} is ${data.summary.beta === null ? 'undefined' : formatNumber(data.summary.beta)}.`
            : undefined
        }
      >
        {risk.isPending && <PanelLoading />}
        {data && (
          <DrawdownChart
            points={data.drawdown_curve}
            maxDepth={data.summary.max_drawdown.depth}
            troughDate={data.summary.max_drawdown.trough_date}
          />
        )}
      </Panel>
    </div>
  )
}
