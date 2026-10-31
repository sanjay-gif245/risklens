import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { VarEstimate } from '../api/types'
import { ChartFrame } from '../components/ChartFrame'
import { ChartTooltip } from '../components/ChartTooltip'
import { axisStyle, colors, gridStyle, percentTick } from '../lib/chartTheme'
import { formatMethod, formatPercent } from '../lib/format'

interface VarChartProps {
  estimates: VarEstimate[]
  confidence: number
  horizon: number
}

export function VarChart({ estimates, confidence, horizon }: VarChartProps) {
  const data = estimates.map((e) => ({
    method: formatMethod(e.method),
    VaR: e.var_pct,
    CVaR: e.cvar_pct,
  }))
  const level = `${Math.round(confidence * 100)}%`
  const summary = `${horizon}-day value at risk at ${level} confidence: ${estimates
    .map((e) => `${formatMethod(e.method)} ${formatPercent(e.var_pct)}`)
    .join(', ')}.`

  return (
    <ChartFrame summary={summary} height={300}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={6}>
          <CartesianGrid {...gridStyle} />
          <XAxis dataKey="method" {...axisStyle} />
          <YAxis tickFormatter={percentTick} width={56} {...axisStyle} />
          <Tooltip
            cursor={{ fill: 'rgb(237 230 214 / 4%)' }}
            content={<ChartTooltip formatValue={(value) => formatPercent(value)} />}
          />
          <Bar dataKey="VaR" fill={colors.gold} barSize={34} isAnimationActive={false} />
          <Bar dataKey="CVaR" fill={colors.oxblood} barSize={34} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
