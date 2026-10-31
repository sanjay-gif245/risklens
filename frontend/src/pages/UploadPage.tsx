import { useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDeletePortfolio, usePortfolios, useUploadPortfolio } from '../api/hooks'
import { Panel } from '../components/Panel'
import { ErrorMessage, Skeleton } from '../components/States'
import { formatDate } from '../lib/format'

function nameFromFile(file: File): string {
  return file.name
    .replace(/\.csv$/i, '')
    .replace(/[_-]+/g, ' ')
    .trim()
}

export function UploadPage() {
  const navigate = useNavigate()
  const portfolios = usePortfolios()
  const upload = useUploadPortfolio()
  const remove = useDeletePortfolio()
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [benchmark, setBenchmark] = useState('')
  const [dragging, setDragging] = useState(false)

  const choose = (chosen: File | undefined) => {
    if (!chosen) return
    setFile(chosen)
    if (!name) setName(nameFromFile(chosen))
    upload.reset()
  }

  const send = (csv: File, portfolioName: string) =>
    upload.mutate(
      { file: csv, name: portfolioName, benchmark },
      { onSuccess: (created) => navigate(`/p/${created.id}`) },
    )

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (file) send(file, name)
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    choose(event.dataTransfer.files[0])
  }

  const loadDemo = async () => {
    const response = await fetch('/sample_portfolio.csv')
    const blob = await response.blob()
    send(new File([blob], 'sample_portfolio.csv', { type: 'text/csv' }), 'Demo portfolio')
  }

  return (
    <div className="stack">
      <div className="intro">
        <div>
          <div className="label">Portfolio risk analytics</div>
          <h1 style={{ marginTop: 12 }}>
            How much could this portfolio lose, and would the model have known?
          </h1>
          <p className="intro__lede">
            Upload your holdings. RiskLens measures volatility, value at risk and what drives them,
            stress tests the portfolio against past crises, then checks its own risk estimates
            against what actually happened.
          </p>
          <ol className="steps">
            <li>Upload a CSV with ticker, quantity and buy price</li>
            <li>Three years of prices are fetched and cached</li>
            <li>Risk, scenarios and a statistical backtest are calculated</li>
          </ol>
        </div>

        <Panel label="New portfolio" title="Upload holdings">
          <form onSubmit={onSubmit} className="stack">
            <label
              className="dropzone"
              data-active={dragging}
              onDragOver={(e) => {
                e.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
            >
              <input
                type="file"
                accept=".csv,text/csv"
                className="visually-hidden"
                onChange={(e: ChangeEvent<HTMLInputElement>) => choose(e.target.files?.[0])}
              />
              {file ? (
                <span className="dropzone__file">{file.name}</span>
              ) : (
                <span className="dropzone__title">Drop a CSV here</span>
              )}
              <span className="muted">
                {file ? 'Choose a different file' : 'or click to browse'}
              </span>
            </label>

            <div className="controls">
              <div className="field field--grow">
                <label className="label" htmlFor="portfolio-name">
                  Portfolio name
                </label>
                <input
                  id="portfolio-name"
                  className="input"
                  value={name}
                  maxLength={100}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="field">
                <label className="label" htmlFor="benchmark">
                  Benchmark (optional)
                </label>
                <input
                  id="benchmark"
                  className="input input--short"
                  style={{ width: 130, textAlign: 'left' }}
                  placeholder="auto"
                  value={benchmark}
                  onChange={(e) => setBenchmark(e.target.value)}
                />
              </div>
            </div>

            <p className="muted" style={{ fontSize: 13, margin: 0 }}>
              Columns: <code className="mono">ticker, quantity, buy_price</code>. Indian stocks use
              the <code className="mono">.NS</code> suffix. One currency per portfolio, up to 50
              holdings.{' '}
              <a href="/sample_portfolio.csv" download>
                Download a sample file
              </a>
              .
            </p>

            {upload.isError && <ErrorMessage error={upload.error} />}

            <div className="controls">
              <button
                type="submit"
                className="button"
                disabled={!file || !name.trim() || upload.isPending}
              >
                {upload.isPending ? 'Fetching prices…' : 'Analyse portfolio'}
              </button>
              <button
                type="button"
                className="button button--quiet"
                disabled={upload.isPending}
                onClick={() => void loadDemo()}
              >
                Use the demo portfolio
              </button>
            </div>
            {upload.isPending && (
              <p className="muted" role="status" style={{ margin: 0 }}>
                Checking every ticker and fetching three years of daily prices. A first upload can
                take up to half a minute.
              </p>
            )}
          </form>
        </Panel>
      </div>

      <Panel label="Saved" title="Your portfolios">
        {portfolios.isPending && <Skeleton height={64} />}
        {portfolios.isError && <ErrorMessage error={portfolios.error} />}
        {portfolios.data?.length === 0 && (
          <p className="muted" style={{ margin: 0 }}>
            Nothing here yet. Upload a file or try the demo portfolio to see the analysis.
          </p>
        )}
        {portfolios.data && portfolios.data.length > 0 && (
          <ul className="portfolio-list">
            {portfolios.data.map((p) => (
              <li key={p.id}>
                <div>
                  <Link to={`/p/${p.id}`} className="portfolio-list__name">
                    {p.name}
                  </Link>
                  <div className="muted" style={{ fontSize: 13 }}>
                    {p.holding_count} holdings &middot; {p.base_currency} &middot; added{' '}
                    {formatDate(p.created_at.slice(0, 10))}
                  </div>
                </div>
                <button
                  type="button"
                  className="link-button"
                  disabled={remove.isPending}
                  onClick={() => {
                    if (window.confirm(`Delete "${p.name}"?`)) remove.mutate(p.id)
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}
