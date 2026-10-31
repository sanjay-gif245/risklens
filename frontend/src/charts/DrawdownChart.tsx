import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ChartFrame } from '../components/ChartFrame'
import { ChartTooltip } from '../components/ChartTooltip'
import { axisStyle, colors, gridStyle, percentTick, tickInterval } from '../lib/chartTheme'
import { formatDate, formatPercent } from '../lib/format'

interface DrawdownChartProps {
  points: { date: string; drawdown: number }[]
  maxDepth: number
  troughDate: string
}

export function DrawdownChart({ points, maxDepth, troughDate }: DrawdownChartProps) {
  const summary = `Fall from the previous peak of the portfolio value. The deepest fall was ${formatPercent(maxDepth)} on ${formatDate(troughDate)}.`
  return (
    <ChartFrame summary={summary} height={280}>
      <ResponsiveContainer>
        <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid {...gridStyle} />
          <XAxis
            dataKey="date"
            tickFormatter={(d: string) => d.slice(0, 7)}
            interval={tickInterval(points.length)}
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
          <Area
            type="monotone"
            dataKey="drawdown"
            name="Drawdown"
            stroke={colors.garnet}
            strokeWidth={1.25}
            fill={colors.oxblood}
            fillOpacity={0.45}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
