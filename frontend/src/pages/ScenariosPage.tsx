import { useEffect, useState } from 'react'
import { useScenario, useScenarioEvents } from '../api/hooks'
import type { PortfolioDetail, ScenarioRequest, ScenarioResponse } from '../api/types'
import { ReplayChart } from '../charts/ReplayChart'
import { PageHead } from '../components/PageHead'
import { Panel } from '../components/Panel'
import { Segmented } from '../components/Segmented'
import { ErrorMessage, Warnings } from '../components/States'
import { formatDate, formatMoney, formatPercent } from '../lib/format'
import { usePortfolioContext } from './portfolioContext'

type Kind = 'market' | 'custom' | 'replay'

const KINDS = [
  { value: 'market' as const, label: 'Market shock' },
  { value: 'custom' as const, label: 'Custom shocks' },
  { value: 'replay' as const, label: 'Historical replay' },
]

const SHOCK_MIN = -40
const SHOCK_MAX = 20

export function ScenariosPage() {
  const { portfolio } = usePortfolioContext()
  const scenario = useScenario(portfolio.id)
  const [kind, setKind] = useState<Kind>('market')

  return (
    <div className="stack">
      <PageHead section="Scenarios" portfolio={portfolio} />
      <Segmented label="Scenario" options={KINDS} value={kind} onChange={setKind} />

      {kind === 'market' && <MarketShock benchmark={portfolio.benchmark} run={scenario.mutate} />}
      {kind === 'custom' && (
        <CustomShocks portfolio={portfolio} run={scenario.mutate} busy={scenario.isPending} />
      )}
      {kind === 'replay' && <Replay run={scenario.mutate} busy={scenario.isPending} />}

      {scenario.isError && <ErrorMessage error={scenario.error} />}
      {scenario.data && scenario.data.type === typeFor(kind) && (
        <Result result={scenario.data} stale={scenario.isPending} />
      )}
      {!scenario.data && !scenario.isPending && kind !== 'market' && (
        <p className="muted">
          Set up the scenario above and run it to see the effect on your holdings.
        </p>
      )}
    </div>
  )
}

function typeFor(kind: Kind): ScenarioResponse['type'] {
  return { market: 'market_shock', custom: 'custom_shocks', replay: 'historical_replay' }[
    kind
  ] as ScenarioResponse['type']
}

interface RunProps {
  run: (body: ScenarioRequest) => void
}

function MarketShock({ benchmark, run }: RunProps & { benchmark: string }) {
  const [move, setMove] = useState(-10)

  // Run shortly after the slider stops moving rather than on every tick
  useEffect(() => {
    const timer = setTimeout(() => run({ type: 'market_shock', benchmark_move: move / 100 }), 300)
    return () => clearTimeout(timer)
  }, [move, run])

  return (
    <Panel
      label="Single-factor"
      title={`${benchmark} moves ${move > 0 ? '+' : ''}${move}%`}
      lede="Each holding moves by its beta to the benchmark times the shock. A quick estimate, not a forecast."
    >
      <label className="label" htmlFor="shock-slider">
        Benchmark move
      </label>
      <input
        id="shock-slider"
        type="range"
        min={SHOCK_MIN}
        max={SHOCK_MAX}
        step={1}
        value={move}
        onChange={(e) => setMove(Number(e.target.value))}
        aria-valuetext={`${move} percent`}
      />
      <div
        className="mono muted"
        style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}
      >
        <span>{SHOCK_MIN}%</span>
        <span>0</span>
        <span>+{SHOCK_MAX}%</span>
      </div>
    </Panel>
  )
}

function CustomShocks({
  portfolio,
  run,
  busy,
}: RunProps & { portfolio: PortfolioDetail; busy: boolean }) {
  const analysed = portfolio.holdings.filter((h) => h.analysed)
  const [inputs, setInputs] = useState<Record<string, string>>({})

  const shocks = Object.fromEntries(
    Object.entries(inputs)
      .filter(([, text]) => text.trim() !== '' && Number.isFinite(Number(text)))
      .map(([ticker, text]) => [ticker, Number(text) / 100]),
  )
  const valid = Object.values(shocks).every((v) => v >= -1) && Object.keys(shocks).length > 0

  return (
    <Panel
      label="Hand-picked"
      title="Shock individual holdings"
      lede="Enter a percentage move for any holding. Holdings left blank stay unchanged."
    >
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th className="num">Current value</th>
              <th className="num">Move, %</th>
            </tr>
          </thead>
          <tbody>
            {analysed.map((h) => (
              <tr key={h.ticker}>
                <td className="ticker">{h.ticker}</td>
                <td className="num">{formatMoney(h.market_value, portfolio.base_currency)}</td>
                <td className="num">
                  <input
                    className="input input--short"
                    type="number"
                    step="any"
                    min={-100}
                    inputMode="decimal"
                    placeholder="0"
                    aria-label={`Percentage move for ${h.ticker}`}
                    value={inputs[h.ticker] ?? ''}
                    onChange={(e) => setInputs({ ...inputs, [h.ticker]: e.target.value })}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 20 }}>
        <button
          type="button"
          className="button"
          disabled={!valid || busy}
          onClick={() => run({ type: 'custom_shocks', shocks })}
        >
          {busy ? 'Calculating…' : 'Run scenario'}
        </button>
      </div>
    </Panel>
  )
}

function Replay({ run, busy }: RunProps & { busy: boolean }) {
  const events = useScenarioEvents()
  const [choice, setChoice] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const custom = choice === 'custom'
  const selected = events.data?.find((e) => e.key === choice)

  const ready = custom ? Boolean(start && end) : Boolean(choice)
  const request = (): ScenarioRequest =>
    custom
      ? { type: 'historical_replay', start_date: start, end_date: end }
      : { type: 'historical_replay', event: choice }

  return (
    <Panel
      label="History"
      title="What if today's portfolio had lived through it?"
      lede="Applies the actual price moves of a past episode to the holdings you own now."
    >
      <div className="controls">
        <div className="field field--grow">
          <label className="label" htmlFor="event">
            Event
          </label>
          <select
            id="event"
            className="select"
            value={choice}
            onChange={(e) => setChoice(e.target.value)}
          >
            <option value="">Choose an event</option>
            {events.data?.map((e) => (
              <option key={e.key} value={e.key}>
                {e.label} ({formatDate(e.start_date)} to {formatDate(e.end_date)})
              </option>
            ))}
            <option value="custom">Custom dates</option>
          </select>
        </div>
        {custom && (
          <>
            <div className="field">
              <label className="label" htmlFor="start">
                From
              </label>
              <input
                id="start"
                type="date"
                className="input"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </div>
            <div className="field">
              <label className="label" htmlFor="end">
                To
              </label>
              <input
                id="end"
                type="date"
                className="input"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </div>
          </>
        )}
        <button
          type="button"
          className="button"
          disabled={!ready || busy}
          onClick={() => run(request())}
        >
          {busy ? 'Fetching history…' : 'Run scenario'}
        </button>
      </div>
      {selected && (
        <p className="muted" style={{ marginTop: 16, marginBottom: 0 }}>
          {selected.description}
        </p>
      )}
    </Panel>
  )
}

function Result({ result, stale }: { result: ScenarioResponse; stale: boolean }) {
  const loss = result.pnl < 0
  const maxAbs = Math.max(...result.holdings.map((h) => Math.abs(h.pnl)), 1)
  return (
    <Panel label="Result" title={result.label}>
      <div style={{ opacity: stale ? 0.5 : 1 }} className="stack">
        <Warnings items={result.notes} />
        <div className="grid-2" style={{ alignItems: 'end' }}>
          <div>
            <div className="label">Profit and loss</div>
            <div className={`result-figure ${loss ? 'negative' : 'positive'}`}>
              {formatMoney(result.pnl, result.currency)}
            </div>
            <div className="mono muted" style={{ marginTop: 8 }}>
              {formatPercent(result.pnl_pct, 2, true)} of{' '}
              {formatMoney(result.covered_value, result.currency)} covered
            </div>
          </div>
          {result.start_date && result.end_date && (
            <div className="muted">
              {formatDate(result.start_date)} to {formatDate(result.end_date)}
            </div>
          )}
        </div>

        {result.path.length > 1 && <ReplayChart path={result.path} />}

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th className="num">Value now</th>
                <th className="num">Move</th>
                <th className="num">Profit / loss</th>
              </tr>
            </thead>
            <tbody>
              {result.holdings.map((h) => (
                <tr key={h.ticker}>
                  <td className="ticker">{h.ticker}</td>
                  <td className="num">{formatMoney(h.value, result.currency)}</td>
                  <td className="num">
                    {h.covered ? (
                      formatPercent(h.shock_return, 1, true)
                    ) : (
                      <span className="muted">no data</span>
                    )}
                  </td>
                  <td className="num">
                    <div className="bar-cell">
                      <span
                        className={`bar-cell__bar ${h.pnl >= 0 ? 'bar-cell__bar--gain' : ''}`}
                        style={{ width: `${(Math.abs(h.pnl) / maxAbs) * 80}px` }}
                      />
                      <span className={h.pnl < 0 ? 'negative' : h.pnl > 0 ? 'positive' : 'muted'}>
                        {formatMoney(h.pnl, result.currency)}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Panel>
  )
}
