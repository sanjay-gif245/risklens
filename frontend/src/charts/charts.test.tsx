import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { BacktestMethodResult, Contribution, Holding, VarEstimate } from '../api/types'
import { AllocationChart } from './AllocationChart'
import { BacktestChart } from './BacktestChart'
import { ContributionChart } from './ContributionChart'
import { CorrelationHeatmap } from './CorrelationHeatmap'
import { VarChart } from './VarChart'

// Charts draw to SVG, which jsdom cannot measure, so these tests check the text alternatives:
// what a screen reader hears and what sits under each chart.

describe('chart summaries', () => {
  it('VarChart states each method in words', () => {
    const estimates: VarEstimate[] = [
      {
        method: 'historical',
        var_pct: 0.0135,
        var_amount: 968,
        cvar_pct: 0.0211,
        cvar_amount: 1511,
      },
      {
        method: 'parametric',
        var_pct: 0.0143,
        var_amount: 1025,
        cvar_pct: null,
        cvar_amount: null,
      },
    ]
    render(<VarChart estimates={estimates} confidence={0.95} horizon={1} />)
    expect(
      screen.getByRole('img', {
        name: '1-day value at risk at 95% confidence: Historical 1.35%, Parametric 1.43%.',
      }),
    ).toBeInTheDocument()
  })

  it('ContributionChart names the holding that drives the most risk', () => {
    const rows: Contribution[] = [
      { ticker: 'KO', weight: 0.08, contribution: 0.002, pct_contribution: 0.012 },
      { ticker: 'AAPL', weight: 0.193, contribution: 0.04, pct_contribution: 0.255 },
    ]
    render(<ContributionChart rows={rows} />)
    expect(
      screen.getByRole('img', {
        name: /AAPL drives the most risk: 25\.5% of risk from 19\.3% of capital/,
      }),
    ).toBeInTheDocument()
  })

  it('AllocationChart reports the largest holding and the count', () => {
    const holding = (ticker: string, value: number, weight: number): Holding => ({
      ticker,
      quantity: 1,
      buy_price: 1,
      last_price: value,
      market_value: value,
      cost_value: 1,
      unrealized_pnl: 0,
      weight,
      history_days: 700,
      analysed: true,
    })
    render(
      <AllocationChart
        currency="USD"
        holdings={[holding('KO', 20, 0.2), holding('AAPL', 80, 0.8)]}
      />,
    )
    expect(
      screen.getByRole('img', { name: /largest holding is AAPL at 80\.0%.*2 holdings/ }),
    ).toBeInTheDocument()
    expect(screen.getByText('KO')).toBeInTheDocument()
  })

  it('BacktestChart states the breach count against the expected rate', () => {
    const result: BacktestMethodResult = {
      method: 'historical',
      confidence: 0.95,
      observations: 3,
      breaches: 1,
      expected_rate: 0.05,
      observed_rate: 1 / 3,
      likelihood_ratio: 1,
      p_value: 0.3,
      rejected: false,
      verdict: 'Model accepted.',
      breach_dates: ['2025-01-03'],
      var: [0.01, 0.01, 0.01],
    }
    render(
      <BacktestChart
        dates={['2025-01-01', '2025-01-02', '2025-01-03']}
        realized={[0.001, -0.002, -0.03]}
        result={result}
      />,
    )
    expect(
      screen.getByRole('img', {
        name: /95% Historical VaR limit.*1 of 3 days; 5\.0% was expected/,
      }),
    ).toBeInTheDocument()
  })
})

describe('CorrelationHeatmap', () => {
  const tickers = ['A', 'B']
  const matrix = [
    [1, 0.42],
    [0.42, 1],
  ]

  it('renders an accessible table with every pair', () => {
    render(<CorrelationHeatmap tickers={tickers} matrix={matrix} />)
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getAllByText('0.42')).toHaveLength(2)
    expect(screen.getByText(/most closely linked pair is A and B at 0\.42/)).toBeInTheDocument()
  })

  it('explains itself when there is a single holding', () => {
    render(<CorrelationHeatmap tickers={['A']} matrix={[[1]]} />)
    expect(screen.getByText(/nothing to be correlated with/)).toBeInTheDocument()
  })
})
