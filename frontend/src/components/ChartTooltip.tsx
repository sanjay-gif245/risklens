interface Entry {
  name?: string | number
  value?: number | string
  color?: string
}

interface ChartTooltipProps {
  active?: boolean
  label?: string | number
  payload?: Entry[]
  formatLabel?: (label: string | number) => string
  formatValue: (value: number, name: string) => string
}

/** Tooltip styled to the palette, replacing Recharts' default white box. */
export function ChartTooltip({
  active,
  label,
  payload,
  formatLabel,
  formatValue,
}: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="tooltip">
      {label !== undefined && (
        <div className="tooltip__title">{formatLabel ? formatLabel(label) : label}</div>
      )}
      {payload.map((entry) =>
        typeof entry.value === 'number' ? (
          <div className="tooltip__row" key={String(entry.name)}>
            <span style={{ color: entry.color }}>{entry.name}</span>
            <span>{formatValue(entry.value, String(entry.name))}</span>
          </div>
        ) : null,
      )}
    </div>
  )
}
