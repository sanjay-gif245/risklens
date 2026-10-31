const GOLD = '201 169 97'
const GARNET = '196 100 110'

/** Positive correlation shades toward gold, negative toward garnet; strength sets the opacity. */
export function cellColor(value: number): string {
  const strength = Math.min(Math.abs(value), 1) * 0.85
  return `rgb(${value >= 0 ? GOLD : GARNET} / ${strength.toFixed(3)})`
}

export interface Pair {
  a: string
  b: string
  value: number
}

/** The off-diagonal pair with the largest absolute correlation, or null for a single holding. */
export function strongestPair(tickers: string[], matrix: number[][]): Pair | null {
  let best: Pair | null = null
  matrix.forEach((row, i) =>
    row.forEach((value, j) => {
      if (j <= i) return
      if (best === null || Math.abs(value) > Math.abs(best.value)) {
        best = { a: tickers[i] ?? '', b: tickers[j] ?? '', value }
      }
    }),
  )
  return best
}
