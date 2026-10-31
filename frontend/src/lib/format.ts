// Number formatting in one place. INR uses Indian digit grouping (12,34,567), USD the usual 1,234,567.

export function formatMoney(value: number, currency: string, decimals = 0): string {
  const locale = currency === 'INR' ? 'en-IN' : 'en-US'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/** 0.0135 -> "1.35%". With `signed`, gains get an explicit plus. */
export function formatPercent(fraction: number, digits = 2, signed = false): string {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    signDisplay: signed ? 'exceptZero' : 'auto',
  }).format(fraction)
}

export function formatNumber(value: number, digits = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

/** "2025-04-08" -> "8 Apr 2025". Parsed as UTC so the day never shifts with the time zone. */
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${iso}T00:00:00Z`))
}

export function formatMethod(method: string): string {
  return (
    { historical: 'Historical', parametric: 'Parametric', monte_carlo: 'Monte Carlo' }[method] ??
    method
  )
}
