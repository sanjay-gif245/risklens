import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, toApiError } from './client'

function respond(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(body === null ? null : JSON.stringify(body), { status, headers })
}

afterEach(() => vi.unstubAllGlobals())

describe('toApiError', () => {
  it('keeps the code, message and details of the API error format', () => {
    const error = toApiError(
      422,
      { code: 'invalid_portfolio_file', message: 'The CSV has 1 problem.', details: [{ row: 2 }] },
      'abc123',
    )
    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('invalid_portfolio_file')
    expect(error.status).toBe(422)
    expect(error.details).toEqual([{ row: 2 }])
    expect(error.requestId).toBe('abc123')
  })

  it('explains a non-JSON server error as a possible cold start', () => {
    const error = toApiError(502, null, null)
    expect(error.code).toBe('unexpected_response')
    expect(error.message).toMatch(/starting/)
  })

  it('handles a client error without the standard body', () => {
    expect(toApiError(400, { detail: 'x' }, null).message).toBe(
      'The request failed with status 400.',
    )
  })
})

describe('api requests', () => {
  it('turns a network failure into a readable error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(api.listPortfolios()).rejects.toMatchObject({
      code: 'network_error',
      status: 0,
    })
  })

  it('throws the API error with the request id from the response header', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          respond(
            404,
            { code: 'portfolio_not_found', message: 'Gone.', details: null },
            { 'X-Request-ID': 'r-1' },
          ),
        ),
    )
    await expect(api.getPortfolio('x')).rejects.toMatchObject({
      code: 'portfolio_not_found',
      requestId: 'r-1',
    })
  })

  it('returns undefined for a 204 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(api.deletePortfolio('x')).resolves.toBeUndefined()
  })

  it('sends confidence, horizon and an optional lookback', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(200, {}))
    vi.stubGlobal('fetch', fetchMock)

    await api.getRisk('p1', { confidence: 0.99, horizon: 5, lookback: null })
    await api.getRisk('p1', { confidence: 0.95, horizon: 1, lookback: 252 })

    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/portfolios/p1/risk?confidence=0.99&horizon=5')
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      '/api/portfolios/p1/risk?confidence=0.95&horizon=1&lookback=252',
    )
  })

  it('uploads the file as multipart form data and omits an empty benchmark', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(201, {}))
    vi.stubGlobal('fetch', fetchMock)

    await api.uploadPortfolio(new File(['a'], 'h.csv'), 'Growth', '  ')

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    const form = init.body as FormData
    expect(init.method).toBe('POST')
    expect(form.get('name')).toBe('Growth')
    expect(form.get('file')).toBeInstanceOf(File)
    expect(form.has('benchmark')).toBe(false)
  })

  it('posts scenarios as JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(200, {}))
    vi.stubGlobal('fetch', fetchMock)

    await api.runScenario('p1', { type: 'market_shock', benchmark_move: -0.1 })

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(JSON.parse(init.body as string)).toEqual({ type: 'market_shock', benchmark_move: -0.1 })
  })
})
