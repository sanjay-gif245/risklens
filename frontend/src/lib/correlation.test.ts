import { describe, expect, it } from 'vitest'
import { cellColor, strongestPair } from './correlation'

describe('cellColor', () => {
  it('shades positive values gold and negative values garnet', () => {
    expect(cellColor(0.5)).toBe('rgb(201 169 97 / 0.425)')
    expect(cellColor(-0.5)).toBe('rgb(196 100 110 / 0.425)')
  })

  it('is fully transparent at zero and capped at full correlation', () => {
    expect(cellColor(0)).toBe('rgb(201 169 97 / 0.000)')
    expect(cellColor(1)).toBe('rgb(201 169 97 / 0.850)')
    expect(cellColor(1.4)).toBe(cellColor(1))
  })
})

describe('strongestPair', () => {
  const tickers = ['A', 'B', 'C']
  const matrix = [
    [1, 0.2, -0.7],
    [0.2, 1, 0.4],
    [-0.7, 0.4, 1],
  ]

  it('finds the pair with the largest absolute correlation', () => {
    expect(strongestPair(tickers, matrix)).toEqual({ a: 'A', b: 'C', value: -0.7 })
  })

  it('returns null when there is nothing to pair', () => {
    expect(strongestPair(['A'], [[1]])).toBeNull()
  })
})
