import { describe, expect, it } from 'vitest'
import { formatDate, formatMethod, formatMoney, formatNumber, formatPercent } from './format'

describe('formatMoney', () => {
  it('groups INR digits the Indian way', () => {
    expect(formatMoney(1234567, 'INR')).toBe('₹12,34,567')
  })

  it('groups USD digits the usual way', () => {
    expect(formatMoney(1234567, 'USD')).toBe('$1,234,567')
  })

  it('keeps the sign on losses and honours decimals', () => {
    expect(formatMoney(-25515.4, 'USD')).toBe('-$25,515')
    expect(formatMoney(344.629, 'USD', 2)).toBe('$344.63')
  })
})

describe('formatPercent', () => {
  it('turns a fraction into a percentage', () => {
    expect(formatPercent(0.01352)).toBe('1.35%')
    expect(formatPercent(0.1912, 1)).toBe('19.1%')
  })

  it('adds an explicit plus only when asked', () => {
    expect(formatPercent(0.24, 1, true)).toBe('+24.0%')
    expect(formatPercent(-0.356, 1, true)).toBe('-35.6%')
    expect(formatPercent(0.24, 1)).toBe('24.0%')
  })
})

describe('formatNumber', () => {
  it('uses fixed decimals and thousands separators', () => {
    expect(formatNumber(0.8408)).toBe('0.84')
    expect(formatNumber(12345.678, 1)).toBe('12,345.7')
  })
})

describe('formatDate', () => {
  it('formats an ISO date without shifting the day', () => {
    expect(formatDate('2025-04-08')).toBe('8 Apr 2025')
    expect(formatDate('2020-03-01')).toBe('1 Mar 2020')
  })
})

describe('formatMethod', () => {
  it('names the three estimators and passes unknown values through', () => {
    expect(formatMethod('monte_carlo')).toBe('Monte Carlo')
    expect(formatMethod('historical')).toBe('Historical')
    expect(formatMethod('other')).toBe('other')
  })
})
