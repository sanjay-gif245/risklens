import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Contribution } from '../api/types'
import { ChartFrame } from '../components/ChartFrame'
import { ChartTooltip } from '../components/ChartTooltip'
import { axisStyle, colors, gridStyle } from '../lib/chartTheme'
import { formatPercent } from '../lib/format'

export function ContributionChart({ rows }: { rows: Contribution[] }) {
  const data = [...rows]
    .sort((a, b) => b.pct_contribution - a.pct_contribution)
    .map((r) => ({ ticker: r.ticker, Weight: r.weight, 'Share of risk': r.pct_contribution }))
  const top = data[0]
  const summary = top
    ? `Share of portfolio risk compared with share of capital. ${top.ticker} drives the most risk: ${formatPercent(top['Share of risk'], 1)} of risk from ${formatPercent(top.Weight, 1)} of capital.`
    : 'No holdings.'

  return (
    <ChartFrame summary={summary} height={Math.max(220, 56 + data.length * 44)}>
      <ResponsiveContainer>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 16, bottom: 0, left: 8 }}
          barGap={3}
        >
          <CartesianGrid {...gridStyle} horizontal={false} vertical />
          <XAxis
            type="number"
            domain={[0, 'auto']}
            tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
            {...axisStyle}
          />
          <YAxis type="category" dataKey="ticker" width={72} {...axisStyle} />
          <Tooltip
            cursor={{ fill: 'rgb(237 230 214 / 4%)' }}
            content={<ChartTooltip formatValue={(value) => formatPercent(value, 1)} />}
          />
          <Bar dataKey="Weight" fill={colors.stoneDim} barSize={10} isAnimationActive={false} />
          <Bar dataKey="Share of risk" fill={colors.gold} barSize={10} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
