import { useEffect, useState, type ReactNode } from 'react'
import { ApiError } from '../api/client'
import type { ApiErrorDetail } from '../api/types'

const SLOW_AFTER_MS = 5000

function useSlowHint(): boolean {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), SLOW_AFTER_MS)
    return () => clearTimeout(timer)
  }, [])
  return slow
}

/** Placeholder block in the palette. Several are stacked to hint at the final layout. */
export function Skeleton({ height = 24, width = '100%' }: { height?: number; width?: string }) {
  return <div className="skeleton" style={{ height, width }} aria-hidden="true" />
}

export function PageLoading({ label = 'Loading' }: { label?: string }) {
  const slow = useSlowHint()
  return (
    <div role="status" aria-live="polite" className="stack">
      <span className="visually-hidden">{label}</span>
      <Skeleton height={56} width="40%" />
      <Skeleton height={120} />
      <Skeleton height={320} />
      {slow && (
        <p className="muted">
          This is taking longer than usual. The server may be waking up after a quiet spell, or
          fetching three years of prices for a new ticker. Hold on a moment.
        </p>
      )}
    </div>
  )
}

export function PanelLoading({ height = 280 }: { height?: number }) {
  return (
    <div role="status" aria-live="polite">
      <span className="visually-hidden">Loading</span>
      <Skeleton height={height} />
    </div>
  )
}

function isDetailList(details: unknown): details is ApiErrorDetail[] {
  return (
    Array.isArray(details) &&
    details.every((d) => typeof d === 'object' && d !== null && 'message' in d)
  )
}

export function ErrorMessage({ error }: { error: Error }) {
  const apiError = error instanceof ApiError ? error : null
  const details = apiError && isDetailList(apiError.details) ? apiError.details : []
  return (
    <div className="banner banner--error" role="alert">
      <div>{error.message}</div>
      {details.length > 0 && (
        <ul>
          {details.map((detail, index) => (
            <li key={index}>
              {detail.row ? `Row ${detail.row}: ` : ''}
              {detail.message}
            </li>
          ))}
        </ul>
      )}
      {apiError?.requestId && (
        <div className="mono muted" style={{ marginTop: 8, fontSize: 12 }}>
          Request {apiError.requestId}
        </div>
      )}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="state">
      <h2 className="state__title">This could not be loaded</h2>
      <div className="state__body">
        <ErrorMessage error={error} />
      </div>
      {onRetry && (
        <button type="button" className="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="state">
      <h2 className="state__title">{title}</h2>
      {children && <div className="state__body">{children}</div>}
    </div>
  )
}

export function Warnings({ items }: { items: string[] }) {
  if (items.length === 0) return null
  return (
    <div>
      {items.map((item) => (
        <div key={item} className="banner" role="note">
          {item}
        </div>
      ))}
    </div>
  )
}
