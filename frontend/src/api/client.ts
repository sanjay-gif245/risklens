import type {
  BacktestResponse,
  PortfolioDetail,
  PortfolioSummary,
  RiskResponse,
  ScenarioEvent,
  ScenarioRequest,
  ScenarioResponse,
} from './types'

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

/** An error the API reported ({code, message, details}) or a failure to reach it at all. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown
  readonly requestId: string | null

  constructor(
    status: number,
    code: string,
    message: string,
    details: unknown = null,
    requestId: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.requestId = requestId
  }
}

interface ErrorBody {
  code?: string
  message?: string
  details?: unknown
}

export function toApiError(status: number, body: unknown, requestId: string | null): ApiError {
  const parsed = (typeof body === 'object' && body !== null ? body : {}) as ErrorBody
  if (parsed.code && parsed.message) {
    return new ApiError(status, parsed.code, parsed.message, parsed.details ?? null, requestId)
  }
  // Not our JSON error format: usually a proxy answering while the API is starting up
  const message =
    status >= 500
      ? 'The server is not responding properly. If it was idle it may still be starting; try again in a moment.'
      : `The request failed with status ${status}.`
  return new ApiError(status, 'unexpected_response', message, null, requestId)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}/api${path}`, init)
  } catch {
    throw new ApiError(
      0,
      'network_error',
      'Cannot reach the RiskLens API. Check your connection and try again.',
    )
  }
  const requestId = response.headers.get('X-Request-ID')
  if (response.status === 204) return undefined as T
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw toApiError(response.status, body, requestId)
  return body as T
}

export const api = {
  listPortfolios: () => request<PortfolioSummary[]>('/portfolios'),
  getPortfolio: (id: string) => request<PortfolioDetail>(`/portfolios/${id}`),
  deletePortfolio: (id: string) => request<void>(`/portfolios/${id}`, { method: 'DELETE' }),
  uploadPortfolio: (file: File, name: string, benchmark: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('name', name)
    if (benchmark.trim()) form.append('benchmark', benchmark.trim())
    return request<PortfolioDetail>('/portfolios', { method: 'POST', body: form })
  },
  getRisk: (
    id: string,
    params: { confidence: number; horizon: number; lookback: number | null },
  ) => {
    const query = new URLSearchParams({
      confidence: String(params.confidence),
      horizon: String(params.horizon),
    })
    if (params.lookback !== null) query.set('lookback', String(params.lookback))
    return request<RiskResponse>(`/portfolios/${id}/risk?${query}`)
  },
  getBacktest: (id: string, window: number) =>
    request<BacktestResponse>(`/portfolios/${id}/backtest?window=${window}`),
  listScenarioEvents: () => request<ScenarioEvent[]>('/scenario-events'),
  runScenario: (id: string, body: ScenarioRequest) =>
    request<ScenarioResponse>(`/portfolios/${id}/scenario`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
}
