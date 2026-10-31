// Shapes returned by the API. They mirror backend/app/schemas. Dates are ISO strings,
// ratios are fractions (0.0135 means 1.35%), and losses are positive numbers.

export interface PortfolioSummary {
  id: string
  name: string
  base_currency: string
  benchmark: string
  created_at: string
  holding_count: number
}

export interface Holding {
  ticker: string
  quantity: number
  buy_price: number
  last_price: number
  market_value: number
  cost_value: number
  unrealized_pnl: number
  weight: number
  history_days: number
  analysed: boolean
}

export interface PortfolioDetail extends PortfolioSummary {
  as_of: string
  total_value: number
  total_cost: number
  unrealized_pnl: number
  holdings: Holding[]
  warnings: string[]
  notices: string[]
}

export type VarMethod = 'historical' | 'parametric' | 'monte_carlo'

export interface VarEstimate {
  method: VarMethod
  var_pct: number
  var_amount: number
  cvar_pct: number | null
  cvar_amount: number | null
}

export interface Contribution {
  ticker: string
  weight: number
  contribution: number
  pct_contribution: number
}

export interface RiskResponse {
  portfolio_id: string
  currency: string
  benchmark: string
  portfolio_value: number
  as_of: string
  confidence: number
  horizon_days: number
  observations: number
  window_start: string
  window_end: string
  summary: {
    annual_return: number
    annual_volatility: number
    sharpe_ratio: number | null
    risk_free_rate: number
    beta: number | null
    correlation_to_benchmark: number | null
    max_drawdown: { depth: number; peak_date: string; trough_date: string }
  }
  var: VarEstimate[]
  contributions: Contribution[]
  correlation: { tickers: string[]; matrix: number[][] }
  drawdown_curve: { date: string; drawdown: number }[]
  excluded: Record<string, number>
  warnings: string[]
}

export interface ScenarioEvent {
  key: string
  label: string
  start_date: string
  end_date: string
  description: string
}

export type ScenarioRequest =
  | { type: 'market_shock'; benchmark_move: number }
  | { type: 'custom_shocks'; shocks: Record<string, number> }
  | { type: 'historical_replay'; event?: string; start_date?: string; end_date?: string }

export interface ScenarioHolding {
  ticker: string
  value: number
  shock_return: number
  pnl: number
  covered: boolean
}

export interface ScenarioResponse {
  portfolio_id: string
  type: ScenarioRequest['type']
  label: string
  start_date: string | null
  end_date: string | null
  currency: string
  total_value: number
  covered_value: number
  pnl: number
  pnl_pct: number
  holdings: ScenarioHolding[]
  path: { date: string; change: number }[]
  notes: string[]
}

export interface BacktestMethodResult {
  method: VarMethod
  confidence: number
  observations: number
  breaches: number
  expected_rate: number
  observed_rate: number
  likelihood_ratio: number
  p_value: number
  rejected: boolean
  verdict: string
  breach_dates: string[]
  var: number[]
}

export interface BacktestResponse {
  portfolio_id: string
  window: number
  start_date: string
  end_date: string
  dates: string[]
  realized_returns: number[]
  results: BacktestMethodResult[]
  warnings: string[]
}

export interface ApiErrorDetail {
  row?: number | null
  field?: string | null
  message: string
}
