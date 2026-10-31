import { useState } from 'react'
import { useBacktest } from '../api/hooks'
import type { VarMethod } from '../api/types'
import { BacktestChart } from '../charts/BacktestChart'
import { PageHead } from '../components/PageHead'
import { Panel } from '../components/Panel'
import { Segmented } from '../components/Segmented'
import { ErrorState, PanelLoading, Warnings } from '../components/States'
import { formatDate, formatMethod, formatNumber, formatPercent } from '../lib/format'
import { usePortfolioContext } from './portfolioContext'

const WINDOWS = [
  { value: 120, label: '120 days' },
  { value: 250, label: '250 days' },
  { value: 500, label: '500 days' },
]
const CONFIDENCE = [
  { value: 0.95, label: '95%' },
  { value: 0.99, label: '99%' },
]
const METHODS: { value: VarMethod; label: string }[] = [
  { value: 'historical', label: 'Historical' },
  { value: 'parametric', label: 'Parametric' },
  { value: 'monte_carlo', label: 'Monte Carlo' },
]

export function BacktestPage() {
  const { portfolio } = usePortfolioContext()
  const [window, setWindow] = useState(250)
  const [confidence, setConfidence] = useState(0.95)
  const [method, setMethod] = useState<VarMethod>('historical')
  const backtest = useBacktest(portfolio.id, window)
  const data = backtest.data
  const selected = data?.results.find((r) => r.method === method && r.confidence === confidence)

  return (
    <div className="stack">
      <PageHead section="Backtest" portfolio={portfolio} />

      <Panel
        label="Does the model work?"
        title="VaR tested against what happened"
        lede="For each day, VaR is estimated using only the days before it, then compared with that day's actual return. A 95% model should be wrong on about 1 day in 20."
      >
        <div className="controls">
          <Segmented
            label="Estimation window"
            options={WINDOWS}
            value={window}
            onChange={setWindow}
          />
          <Segmented
            label="Confidence"
            options={CONFIDENCE}
            value={confidence}
            onChange={setConfidence}
          />
          <Segmented label="Method" options={METHODS} value={method} onChange={setMethod} />
        </div>
      </Panel>

      {backtest.isPending && <PanelLoading height={420} />}
      {backtest.isError && (
        <ErrorState error={backtest.error} onRetry={() => void backtest.refetch()} />
      )}
      {data && <Warnings items={data.warnings} />}

      {data && selected && (
        <Panel
          label={`${formatMethod(method)}, ${Math.round(confidence * 100)}%`}
          title={`${selected.breaches} breaches in ${selected.observations} days`}
          lede={`${formatDate(data.start_date)} to ${formatDate(data.end_date)}. Red points are days on which the loss was larger than the VaR limit.`}
        >
          <BacktestChart dates={data.dates} realized={data.realized_returns} result={selected} />
          <p style={{ marginTop: 20, marginBottom: 0 }}>
            <span className={selected.rejected ? 'badge badge--bad' : 'badge badge--ok'}>
              {selected.rejected ? 'Rejected' : 'Accepted'}
            </span>{' '}
            {selected.verdict}
          </p>
        </Panel>
      )}

      {data && (
        <Panel
          label="Kupiec test"
          title="All methods side by side"
          lede="The proportion-of-failures test asks whether the observed breach rate is consistent with the rate the model promises."
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Method</th>
                  <th className="num">Level</th>
                  <th className="num">Breaches</th>
                  <th className="num">Expected rate</th>
                  <th className="num">Observed rate</th>
                  <th className="num">LR statistic</th>
                  <th className="num">p-value</th>
                  <th>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r) => (
                  <tr key={`${r.method}-${r.confidence}`}>
                    <td>{formatMethod(r.method)}</td>
                    <td className="num">{Math.round(r.confidence * 100)}%</td>
                    <td className="num">
                      {r.breaches} / {r.observations}
                    </td>
                    <td className="num">{formatPercent(r.expected_rate)}</td>
                    <td className="num">{formatPercent(r.observed_rate)}</td>
                    <td className="num">{formatNumber(r.likelihood_ratio)}</td>
                    <td className="num">{formatNumber(r.p_value, 3)}</td>
                    <td>
                      <span className={r.rejected ? 'badge badge--bad' : 'badge badge--ok'}>
                        {r.rejected ? 'Rejected at 5%' : 'Accepted at 5%'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="prose" style={{ marginTop: 24 }}>
            <h3>How to read this</h3>
            <p>
              A p-value below 0.05 means the breach count is too far from what the model promises
              for the gap to be luck, so the model is rejected. The test is two-sided: a model that
              breaches far less often than promised is rejected too, because it is overly cautious.
              Accepted does not prove a model is right; with only a few hundred days the test cannot
              reject a model that is modestly wrong, particularly at 99%.
            </p>
          </div>
        </Panel>
      )}
    </div>
  )
}
