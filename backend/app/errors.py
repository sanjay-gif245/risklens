"""Errors the API reports to clients as {code, message, details}.

Services raise these; the API layer turns them into JSON responses. Anything
not listed here is a bug and surfaces as a generic 500.
"""

from typing import Any


class AppError(Exception):
    status_code = 400
    code = "app_error"

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidPortfolioFile(AppError):
    """The uploaded CSV or its contents break a rule. details lists each problem."""

    status_code = 422
    code = "invalid_portfolio_file"


class UnknownTickers(AppError):
    status_code = 422
    code = "unknown_ticker"

    def __init__(self, tickers: list[str]) -> None:
        listed = ", ".join(tickers)
        super().__init__(
            f"No price data found for: {listed}. Check the symbols; "
            "Indian stocks need the .NS suffix, for example RELIANCE.NS.",
            {"tickers": tickers},
        )


class InvalidRequest(AppError):
    """The request is well-formed but asks for something that cannot be computed."""

    status_code = 422
    code = "invalid_request"


class FileTooLarge(AppError):
    status_code = 413
    code = "file_too_large"


class InsufficientData(AppError):
    status_code = 422
    code = "insufficient_data"


class PortfolioNotFound(AppError):
    status_code = 404
    code = "portfolio_not_found"

    def __init__(self, portfolio_id: object) -> None:
        super().__init__(f"Portfolio {portfolio_id} does not exist.")


class ProviderUnavailable(AppError):
    status_code = 502
    code = "price_provider_unavailable"


class DatabaseUnavailable(AppError):
    status_code = 503
    code = "database_unavailable"
