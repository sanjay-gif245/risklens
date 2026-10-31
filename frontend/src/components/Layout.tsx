import { Link, NavLink, Outlet, useMatch } from 'react-router-dom'

export function Layout() {
  const portfolioRoute = useMatch('/p/:id/*')
  const base = portfolioRoute ? `/p/${portfolioRoute.params.id}` : null

  return (
    <>
      <header className="header">
        <div className="header__inner">
          <Link to="/" className="wordmark" aria-label="RiskLens, home">
            Risk<em>Lens</em>
          </Link>
          <nav className="nav" aria-label="Sections">
            {base && (
              <>
                <NavLink to={base} end>
                  Overview
                </NavLink>
                <NavLink to={`${base}/risk`}>Risk</NavLink>
                <NavLink to={`${base}/scenarios`}>Scenarios</NavLink>
                <NavLink to={`${base}/backtest`}>Backtest</NavLink>
              </>
            )}
            <NavLink to="/methodology">Methodology</NavLink>
          </nav>
          <div className="header__side">
            <Link to="/">All portfolios</Link>
          </div>
        </div>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </>
  )
}
