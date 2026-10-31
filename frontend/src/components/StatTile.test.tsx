import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatTile } from './StatTile'

describe('StatTile', () => {
  it('shows the formatted value and its note', () => {
    render(
      <StatTile
        label="Annual volatility"
        value={0.1474}
        format={(v) => `${(v * 100).toFixed(1)}%`}
        note="daily returns"
      />,
    )
    expect(screen.getByText('Annual volatility')).toBeInTheDocument()
    expect(screen.getByLabelText('14.7%')).toBeInTheDocument()
    expect(screen.getByText('daily returns')).toBeInTheDocument()
  })

  it('shows a dash and an accessible label when there is no value', () => {
    render(<StatTile label="Beta" value={null} format={(v) => String(v)} />)
    expect(screen.getByLabelText('not available')).toHaveTextContent('—')
  })
})
