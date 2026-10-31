import type { ReactNode } from 'react'

interface ChartFrameProps {
  /** One sentence stating what the chart shows, in words. Read by screen readers and shown below. */
  summary: string
  height: number
  children: ReactNode
}

export function ChartFrame({ summary, height, children }: ChartFrameProps) {
  return (
    <figure className="chart">
      <div role="img" aria-label={summary} style={{ height }}>
        {children}
      </div>
      <figcaption className="chart__caption">{summary}</figcaption>
    </figure>
  )
}
