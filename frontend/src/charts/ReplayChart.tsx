import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ChartFrame } from '../components/ChartFrame'
import { ChartTooltip } from '../components/ChartTooltip'
import { axisStyle, colors, gridStyle, percentTick, tickInterval } from '../lib/chartTheme'
import { formatDate, formatPercent } from '../lib/format'

export function ReplayChart({ path }: { path: { date: string; change: number }[] }) {
  const last = path[path.length - 1]
  const summary = last
    ? `Value of today's portfolio through the event, relative to the start. It ends ${formatPercent(last.change, 1, true)} on ${formatDate(last.date)}.`
    : 'No path available.'
  return (
    <ChartFrame summary={summary} height={260}>
      <ResponsiveContainer>
        <LineChart data={path} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid {...gridStyle} />
          <XAxis
            dataKey="date"
            tickFormatter={(d: string) => d.slice(5)}
            interval={tickInterval(path.length, 5)}
            {...axisStyle}
          />
          <YAxis tickFormatter={percentTick} width={56} {...axisStyle} />
          <ReferenceLine y={0} stroke={colors.hairline} />
          <Tooltip
            content={
              <ChartTooltip
                formatLabel={(label) => formatDate(String(label))}
                formatValue={(value) => formatPercent(value, 2, true)}
              />
            }
          />
          <Line
            type="monotone"
            dataKey="change"
            name="Portfolio"
            stroke={colors.gold}
            strokeWidth={1.75}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
