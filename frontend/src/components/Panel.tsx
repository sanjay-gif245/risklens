import type { ReactNode } from 'react'

interface PanelProps {
  label?: string
  title: string
  lede?: string
  children: ReactNode
}

export function Panel({ label, title, lede, children }: PanelProps) {
  return (
    <section className="panel">
      <header className="panel__head">
        {label && <div className="label">{label}</div>}
        <h2 className="panel__title">{title}</h2>
        {lede && <p className="panel__lede">{lede}</p>}
      </header>
      {children}
    </section>
  )
}
