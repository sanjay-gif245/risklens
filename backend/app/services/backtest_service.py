"""Run the rolling VaR backtest for every method at 95% and 99%."""

import uuid

from app.core.backtest import BacktestResult, backtest_var
from app.core.var import VarMethod
from app.errors import InsufficientData
from app.schemas.backtest import BacktestMethodResult, BacktestResponse
from app.services.portfolio_service import MarketData

METHODS: tuple[VarMethod, ...] = ("historical", "parametric", "monte_carlo")
CONFIDENCE_LEVELS = (0.95, 0.99)
MIN_TEST_DAYS = 60
# Below this many expected breaches the Kupiec test can hardly tell good from bad
LOW_POWER_EXPECTED_BREACHES = 5


def run_backtests(portfolio_id: uuid.UUID, market: MarketData, window: int) -> BacktestResponse:
    available = len(market.returns)
    if available < window + MIN_TEST_DAYS:
        raise InsufficientData(
            f"The backtest needs at least {window + MIN_TEST_DAYS} trading days "
            f"({window} to estimate VaR plus {MIN_TEST_DAYS} to test it); "
            f"only {available} are available."
        )

    runs = [
        backtest_var(market.returns, market.weights, method, confidence, window)
        for confidence in CONFIDENCE_LEVELS
        for method in METHODS
    ]
    reference = runs[0]
    dates = [timestamp.date() for timestamp in reference.var_series.index]

    warnings = list(market.warnings)
    for confidence in CONFIDENCE_LEVELS:
        expected = (1 - confidence) * len(dates)
        if expected < LOW_POWER_EXPECTED_BREACHES:
            warnings.append(
                f"At {confidence:.0%} only {expected:.1f} breaches are expected over "
                f"{len(dates)} test days, so the Kupiec test has little power at this level."
            )

    return BacktestResponse(
        portfolio_id=portfolio_id,
        window=window,
        start_date=dates[0],
        end_date=dates[-1],
        dates=dates,
        realized_returns=[float(v) for v in reference.realized],
        results=[_method_result(run) for run in runs],
        warnings=warnings,
    )


def _method_result(run: BacktestResult) -> BacktestMethodResult:
    kupiec = run.kupiec
    return BacktestMethodResult(
        method=run.method,
        confidence=run.confidence,
        observations=kupiec.observations,
        breaches=kupiec.breaches,
        expected_rate=kupiec.expected_rate,
        observed_rate=kupiec.observed_rate,
        likelihood_ratio=kupiec.likelihood_ratio,
        p_value=kupiec.p_value,
        rejected=kupiec.rejected,
        verdict=kupiec.verdict,
        breach_dates=[timestamp.date() for timestamp in run.breach_dates],
        var=[float(v) for v in run.var_series],
    )
