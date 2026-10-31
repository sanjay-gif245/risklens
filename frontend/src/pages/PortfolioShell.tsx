import { Outlet, useParams } from 'react-router-dom'
import { usePortfolio } from '../api/hooks'
import { ErrorState, PageLoading } from '../components/States'

/** Loads the portfolio named in the URL once, then renders whichever section page is active. */
export function PortfolioShell() {
  const { id = '' } = useParams()
  const query = usePortfolio(id)

  if (query.isPending) return <PageLoading label="Loading portfolio" />
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  return <Outlet context={{ portfolio: query.data }} />
}
