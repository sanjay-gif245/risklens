import { useCountUp } from '../hooks/useCountUp'

interface StatTileProps {
  label: string
  value: number | null
  format: (value: number) => string
  note?: string
  accent?: boolean
}

export function StatTile({ label, value, format, note, accent = false }: StatTileProps) {
  const shown = useCountUp(value ?? 0)
  return (
    <div className={accent ? 'tile tile--accent' : 'tile'}>
      <div className="label">{label}</div>
      <div className="tile__value" aria-label={value === null ? 'not available' : format(value)}>
        <span aria-hidden="true">{value === null ? '—' : format(shown)}</span>
      </div>
      {note && <div className="tile__note">{note}</div>}
    </div>
  )
}
