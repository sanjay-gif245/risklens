import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { BacktestMethodResult } from '../api/types'
import { ChartFrame } from '../components/ChartFrame'
import { ChartTooltip } from '../components/ChartTooltip'
import { axisStyle, colors, gridStyle, percentTick, tickInterval } from '../lib/chartTheme'
import { formatDate, formatMethod, formatPercent } from '../lib/format'

interface BacktestChartProps {
  dates: string[]
  realized: number[]
  result: BacktestMethodResult
}

export function BacktestChart({ dates, realized, result }: BacktestChartProps) {
  const breaches = new Set(result.breach_dates)
  const data = dates.map((date, i) => {
    const value = realized[i] ?? 0
    return {
      date,
      'Daily return': value,
      'VaR limit': -(result.var[i] ?? 0),
      Breach: breaches.has(date) ? value : null,
    }
  })
  const level = `${Math.round(result.confidence * 100)}%`
  const summary = `Daily portfolio returns against the ${level} ${formatMethod(result.method)} VaR limit. The loss went beyond the limit on ${result.breaches} of ${result.observations} days; ${formatPercent(result.expected_rate, 1)} was expected.`

  return (
    <ChartFrame summary={summary} height={340}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
          <CartesianGrid {...gridStyle} />
          <XAxis
            dataKey="date"
            tickFormatter={(d: string) => d.slice(0, 7)}
            interval={tickInterval(data.length)}
            {...axisStyle}
          />
          <YAxis tickFormatter={percentTick} width={56} {...axisStyle} />
          <Tooltip
            content={
              <ChartTooltip
                formatLabel={(label) => formatDate(String(label))}
                formatValue={(value) => formatPercent(value)}
              />
            }
          />
          <Line
            type="linear"
            dataKey="Daily return"
            stroke={colors.stone}
            strokeWidth={1}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="stepAfter"
            dataKey="VaR limit"
            stroke={colors.gold}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          <Scatter dataKey="Breach" fill={colors.garnet} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
