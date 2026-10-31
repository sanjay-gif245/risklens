import { useRisk } from '../api/hooks'
import { AllocationChart } from '../charts/AllocationChart'
import { PageHead } from '../components/PageHead'
import { Panel } from '../components/Panel'
import { StatTile } from '../components/StatTile'
import { ErrorState, PanelLoading, Skeleton, Warnings } from '../components/States'
import { formatMoney, formatNumber, formatPercent } from '../lib/format'
import { usePortfolioContext } from './portfolioContext'

export function OverviewPage() {
  const { portfolio } = usePortfolioContext()
  const risk = useRisk(portfolio.id, 0.95, 1, null)
  const currency = portfolio.base_currency
  const historical = risk.data?.var.find((e) => e.method === 'historical')
  const summary = risk.data?.summary

  const warnings = [...new Set([...portfolio.warnings, ...(risk.data?.warnings ?? [])])]

  return (
    <div className="stack">
      <PageHead section="Overview" portfolio={portfolio} />
      <Warnings items={[...portfolio.notices, ...warnings]} />

      <div className="tiles">
        <StatTile
          accent
          label="Portfolio value"
          value={portfolio.total_value}
          format={(v) => formatMoney(v, currency)}
          note={`${formatPercent(portfolio.unrealized_pnl / portfolio.total_cost, 1, true)} on cost`}
        />
        {risk.isPending && (
          <div className="tile" style={{ gridColumn: 'span 3' }}>
            <Skeleton height={86} />
          </div>
        )}
        {risk.isError && (
          <div className="tile" style={{ gridColumn: 'span 3' }}>
            <ErrorState error={risk.error} onRetry={() => void risk.refetch()} />
          </div>
        )}
        {summary && historical && (
          <>
            <StatTile
              label="Annual volatility"
              value={summary.annual_volatility}
              format={(v) => formatPercent(v, 1)}
              note="daily returns x √252"
            />
            <StatTile
              label="1-day VaR, 95%"
              value={historical.var_amount}
              format={(v) => formatMoney(v, currency)}
              note={`${formatPercent(historical.var_pct)} of value, historical`}
            />
            <StatTile
              label="1-day CVaR, 95%"
              value={historical.cvar_amount}
              format={(v) => formatMoney(v, currency)}
              note="average loss beyond VaR"
            />
          </>
        )}
      </div>

      {summary && (
        <div className="tiles">
          <StatTile
            label={`Beta vs ${portfolio.benchmark}`}
            value={summary.beta}
            format={(v) => formatNumber(v)}
            note={
              summary.correlation_to_benchmark === null
                ? undefined
                : `correlation ${formatNumber(summary.correlation_to_benchmark)}`
            }
          />
          <StatTile
            label="Sharpe ratio"
            value={summary.sharpe_ratio}
            format={(v) => formatNumber(v)}
            note={`risk-free ${formatPercent(summary.risk_free_rate, 1)}`}
          />
          <StatTile
            label="Max drawdown"
            value={summary.max_drawdown.depth}
            format={(v) => formatPercent(v, 1)}
            note={`trough ${summary.max_drawdown.trough_date}`}
          />
          <StatTile
            label="Annual return"
            value={summary.annual_return}
            format={(v) => formatPercent(v, 1, true)}
            note={`${risk.data?.observations} trading days`}
          />
        </div>
      )}

      <div className="grid-wide-narrow">
        <Panel label="Holdings" title="Positions">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th className="num">Quantity</th>
                  <th className="num">Last price</th>
                  <th className="num">Value</th>
                  <th className="num">Weight</th>
                  <th className="num">Gain / loss</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.holdings.map((h) => (
                  <tr key={h.ticker}>
                    <td className="ticker">{h.ticker}</td>
                    <td className="num">{formatNumber(h.quantity, h.quantity % 1 ? 2 : 0)}</td>
                    <td className="num">{formatMoney(h.last_price, currency, 2)}</td>
                    <td className="num">{formatMoney(h.market_value, currency)}</td>
                    <td className="num">{formatPercent(h.weight, 1)}</td>
                    <td className={`num ${h.unrealized_pnl >= 0 ? 'positive' : 'negative'}`}>
                      {formatMoney(h.unrealized_pnl, currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel label="Allocation" title="By market value">
          {portfolio.holdings.length > 0 ? (
            <AllocationChart holdings={portfolio.holdings} currency={currency} />
          ) : (
            <PanelLoading />
          )}
        </Panel>
      </div>
    </div>
  )
}
