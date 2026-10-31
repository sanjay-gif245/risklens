from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analysis, health, portfolios
from app.api.error_handlers import register_error_handlers
from app.api.middleware import RequestContextMiddleware
from app.config import get_settings
from app.logging_config import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="RiskLens API",
        version="0.1.0",
        description=(
            "Portfolio risk analytics: volatility, VaR, CVaR, risk contributions, "
            "stress scenarios and a VaR backtest with the Kupiec test."
        ),
    )
    # Added last = outermost, so CORS headers also cover errors raised by the middleware below
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    register_error_handlers(app)
    for router in (health.router, portfolios.router, analysis.router):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
