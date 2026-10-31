import type { ReactNode } from 'react'
import type { PortfolioDetail } from '../api/types'
import { formatDate } from '../lib/format'

interface PageHeadProps {
  section: string
  portfolio: PortfolioDetail
  children?: ReactNode
}

export function PageHead({ section, portfolio, children }: PageHeadProps) {
  return (
    <div className="page-head">
      <div>
        <div className="label">{section}</div>
        <h1>{portfolio.name}</h1>
        <p className="page-head__meta">
          {portfolio.base_currency} &middot; benchmark {portfolio.benchmark} &middot; prices as of{' '}
          {formatDate(portfolio.as_of)}
        </p>
      </div>
      {children}
    </div>
  )
}
