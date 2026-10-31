// Chart colours. These mirror the tokens in theme/theme.css; Recharts needs literal values.

export const colors = {
  gold: '#c9a961',
  goldDeep: '#b8975a',
  sage: '#8fa68a',
  sageDeep: '#5d7659',
  bone: '#ede6d6',
  stone: '#a39e91',
  stoneDim: '#8a8579',
  garnet: '#c4646e',
  oxblood: '#7d2b34',
  hairline: '#26322d',
  surface: '#111815',
} as const

/** Slice colours for allocation: distinct enough to tell apart, all from the palette. */
export const sliceColors = [
  colors.gold,
  colors.sage,
  colors.bone,
  colors.goldDeep,
  colors.sageDeep,
  colors.stone,
  colors.garnet,
] as const

export const axisStyle = {
  tick: { fill: colors.stone, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" },
  axisLine: { stroke: colors.hairline },
  tickLine: false,
} as const

export const gridStyle = { stroke: colors.hairline, vertical: false } as const

export function percentTick(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

/** Show roughly `count` evenly spaced x-axis labels out of a long series. */
export function tickInterval(length: number, count = 6): number {
  return Math.max(0, Math.floor(length / count) - 1)
}
