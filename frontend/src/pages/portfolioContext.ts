import { useOutletContext } from 'react-router-dom'
import type { PortfolioDetail } from '../api/types'

export interface PortfolioContext {
  portfolio: PortfolioDetail
}

/** The portfolio loaded by PortfolioShell, available to every page nested under /p/:id. */
export function usePortfolioContext(): PortfolioContext {
  return useOutletContext<PortfolioContext>()
}
