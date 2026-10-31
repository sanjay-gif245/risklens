import { Link, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { EmptyState } from './components/States'
import { BacktestPage } from './pages/BacktestPage'
import { MethodologyPage } from './pages/MethodologyPage'
import { OverviewPage } from './pages/OverviewPage'
import { PortfolioShell } from './pages/PortfolioShell'
import { RiskPage } from './pages/RiskPage'
import { ScenariosPage } from './pages/ScenariosPage'
import { UploadPage } from './pages/UploadPage'

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<UploadPage />} />
        <Route path="methodology" element={<MethodologyPage />} />
        <Route path="p/:id" element={<PortfolioShell />}>
          <Route index element={<OverviewPage />} />
          <Route path="risk" element={<RiskPage />} />
          <Route path="scenarios" element={<ScenariosPage />} />
          <Route path="backtest" element={<BacktestPage />} />
        </Route>
        <Route
          path="*"
          element={
            <EmptyState title="Page not found">
              <Link to="/">Back to your portfolios</Link>
            </EmptyState>
          }
        />
      </Route>
    </Routes>
  )
}
