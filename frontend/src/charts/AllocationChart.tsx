import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { Holding } from '../api/types'
import { ChartFrame } from '../components/ChartFrame'
import { ChartTooltip } from '../components/ChartTooltip'
import { colors, sliceColors } from '../lib/chartTheme'
import { formatMoney, formatPercent } from '../lib/format'

const MAX_SLICES = 7

interface Slice {
  name: string
  value: number
  weight: number
  color: string
}

/** The largest holdings keep their own slice; the rest are grouped so the ring stays legible. */
function toSlices(holdings: Holding[]): Slice[] {
  const sorted = [...holdings].sort((a, b) => b.market_value - a.market_value)
  const named = sorted.slice(0, MAX_SLICES)
  const rest = sorted.slice(MAX_SLICES)
  const slices: Slice[] = named.map((h, i) => ({
    name: h.ticker,
    value: h.market_value,
    weight: h.weight,
    color: sliceColors[i % sliceColors.length] ?? colors.stone,
  }))
  if (rest.length > 0) {
    slices.push({
      name: `${rest.length} other${rest.length > 1 ? 's' : ''}`,
      value: rest.reduce((sum, h) => sum + h.market_value, 0),
      weight: rest.reduce((sum, h) => sum + h.weight, 0),
      color: colors.stoneDim,
    })
  }
  return slices
}

export function AllocationChart({ holdings, currency }: { holdings: Holding[]; currency: string }) {
  const slices = toSlices(holdings)
  const top = slices[0]
  const summary = top
    ? `Allocation by market value. The largest holding is ${top.name} at ${formatPercent(top.weight, 1)}; there are ${holdings.length} holdings in total.`
    : 'No holdings.'

  return (
    <div>
      <ChartFrame summary={summary} height={240}>
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="name"
              innerRadius="68%"
              outerRadius="92%"
              paddingAngle={1.5}
              stroke={colors.surface}
              strokeWidth={2}
              isAnimationActive={false}
            >
              {slices.map((slice) => (
                <Cell key={slice.name} fill={slice.color} />
              ))}
            </Pie>
            <Tooltip
              content={<ChartTooltip formatValue={(value) => formatMoney(value, currency)} />}
            />
          </PieChart>
        </ResponsiveContainer>
      </ChartFrame>
      <ul className="legend">
        {slices.map((slice) => (
          <li key={slice.name}>
            <i style={{ background: slice.color }} />
            <span className="ticker">{slice.name}</span>{' '}
            <span className="mono">{formatPercent(slice.weight, 1)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
