"""Assemble every risk figure for one portfolio from its market data."""

import uuid

import pandas as pd

from app.core.attribution import correlation_matrix, risk_contributions
from app.core.metrics import (
    annualized_return,
    annualized_volatility,
    beta,
    correlation,
    drawdown_curve,
    max_drawdown,
    sharpe_ratio,
)
from app.core.returns import portfolio_returns
from app.core.var import (
    DEFAULT_SIMULATIONS,
    historical_cvar,
    historical_var,
    parametric_var,
    simulate_portfolio_returns,
    standard_normals,
)
from app.errors import InsufficientData, InvalidRequest
from app.schemas.risk import (
    ContributionOut,
    CorrelationOut,
    DrawdownOut,
    DrawdownPoint,
    RiskResponse,
    RiskSummary,
    VarEstimate,
)
from app.services.portfolio_service import MarketData

MIN_OBSERVATIONS = 60


def compute_risk(
    portfolio_id: uuid.UUID,
    market: MarketData,
    confidence: float,
    horizon: int,
    lookback: int | None,
    risk_free_rate: float,
) -> RiskResponse:
    """Risk figures over the last `lookback` trading days (all available if None)."""
    warnings = list(market.warnings)
    returns = market.returns
    if lookback is not None:
        if lookback > len(returns):
            warnings.append(
                f"Only {len(returns)} trading days are available; the lookback of "
                f"{lookback} was reduced to that."
            )
        returns = returns.tail(lookback)
    if len(returns) < MIN_OBSERVATIONS:
        raise InvalidRequest(
            f"At least {MIN_OBSERVATIONS} trading days are needed; got {len(returns)}."
        )

    weights = market.weights
    portfolio = portfolio_returns(returns, weights)
    benchmark = market.benchmark_returns.reindex(returns.index)
    covariance = returns.cov()
    value = float(market.values.sum())

    annual_return = annualized_return(portfolio)
    annual_volatility = annualized_volatility(portfolio)
    drawdown = max_drawdown(portfolio)
    summary = RiskSummary(
        annual_return=annual_return,
        annual_volatility=annual_volatility,
        sharpe_ratio=sharpe_ratio(annual_return, annual_volatility, risk_free_rate),
        risk_free_rate=risk_free_rate,
        beta=beta(portfolio, benchmark),
        correlation_to_benchmark=correlation(portfolio, benchmark),
        max_drawdown=DrawdownOut(
            depth=drawdown.depth,
            peak_date=drawdown.peak_date.date(),
            trough_date=drawdown.trough_date.date(),
        ),
    )

    try:
        contributions = risk_contributions(covariance, weights)
    except ValueError as exc:
        raise InsufficientData("The portfolio has zero variance over this window.") from exc

    ordered_weights = weights.reindex(returns.columns).to_numpy()
    simulated = simulate_portfolio_returns(
        returns.mean().to_numpy(),
        covariance.to_numpy(),
        ordered_weights,
        standard_normals(DEFAULT_SIMULATIONS, returns.shape[1]),
    )
    sample = portfolio.to_numpy()
    estimates = [
        _estimate(
            "historical",
            historical_var(sample, confidence, horizon),
            historical_cvar(sample, confidence, horizon),
            value,
        ),
        _estimate("parametric", parametric_var(sample, confidence, horizon), None, value),
        _estimate(
            "monte_carlo",
            historical_var(simulated, confidence, horizon),
            historical_cvar(simulated, confidence, horizon),
            value,
        ),
    ]

    correlations = correlation_matrix(returns)
    return RiskResponse(
        portfolio_id=portfolio_id,
        currency=market.currency,
        benchmark=market.benchmark,
        portfolio_value=value,
        as_of=market.as_of,
        confidence=confidence,
        horizon_days=horizon,
        observations=len(returns),
        window_start=returns.index[0].date(),
        window_end=returns.index[-1].date(),
        summary=summary,
        var=estimates,
        contributions=[
            ContributionOut(
                ticker=str(ticker),
                weight=float(row.weight),
                contribution=float(row.contribution),
                pct_contribution=float(row.pct_contribution),
            )
            for ticker, row in contributions.iterrows()
        ],
        correlation=CorrelationOut(
            tickers=[str(t) for t in correlations.columns],
            matrix=correlations.to_numpy().tolist(),
        ),
        drawdown_curve=_drawdown_points(portfolio),
        excluded=market.excluded,
        warnings=warnings,
    )


def _estimate(method: str, var: float, cvar: float | None, value: float) -> VarEstimate:
    return VarEstimate.model_validate(
        {
            "method": method,
            "var_pct": var,
            "var_amount": var * value,
            "cvar_pct": cvar,
            "cvar_amount": None if cvar is None else cvar * value,
        }
    )


def _drawdown_points(portfolio: pd.Series) -> list[DrawdownPoint]:
    curve = drawdown_curve(portfolio)
    return [
        DrawdownPoint(date=timestamp.date(), drawdown=float(value))
        for timestamp, value in zip(curve.index, curve, strict=True)
    ]
