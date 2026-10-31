import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { UploadPage } from './UploadPage'

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <UploadPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status })
}

afterEach(() => vi.unstubAllGlobals())

describe('UploadPage', () => {
  it('shows an empty state when there are no saved portfolios', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(200, [])))
    renderPage()
    expect(await screen.findByText(/Nothing here yet/)).toBeInTheDocument()
  })

  it('lists saved portfolios', async () => {
    const saved = [
      {
        id: 'p1',
        name: 'Growth',
        base_currency: 'USD',
        benchmark: '^GSPC',
        created_at: '2026-10-31T10:00:00Z',
        holding_count: 8,
      },
    ]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(200, saved)))
    renderPage()
    expect(await screen.findByRole('link', { name: 'Growth' })).toHaveAttribute('href', '/p/p1')
  })

  it('keeps the submit button disabled until a file is chosen', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(200, [])))
    renderPage()
    await screen.findByText(/Nothing here yet/)
    expect(screen.getByRole('button', { name: 'Analyse portfolio' })).toBeDisabled()
  })

  it('names the file after the upload and lists each row-level problem', async () => {
    const problems = [
      { row: 2, field: 'quantity', message: "quantity 'abc' is not a number." },
      { row: 3, field: 'buy_price', message: 'buy_price must be greater than zero (got 0).' },
    ]
    const fetchMock = vi.fn((_url: string, init?: RequestInit) =>
      Promise.resolve(
        init?.method === 'POST'
          ? json(422, {
              code: 'invalid_portfolio_file',
              message: 'The CSV has 2 problems. Fix them and upload again.',
              details: problems,
            })
          : json(200, []),
      ),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, {
      target: { files: [new File(['ticker,quantity,buy_price'], 'my_holdings.csv')] },
    })
    expect(screen.getByLabelText('Portfolio name')).toHaveValue('my holdings')

    fireEvent.click(screen.getByRole('button', { name: 'Analyse portfolio' }))

    const alert = await screen.findByRole('alert')
    await waitFor(() => expect(alert).toHaveTextContent('The CSV has 2 problems'))
    expect(alert).toHaveTextContent("Row 2: quantity 'abc' is not a number.")
    expect(alert).toHaveTextContent('Row 3: buy_price must be greater than zero (got 0).')
  })
})
