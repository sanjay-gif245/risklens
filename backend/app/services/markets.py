"""Which currency and default benchmark a ticker implies."""

from app.errors import InvalidPortfolioFile

INDIAN_SUFFIXES = (".NS", ".BO")
DEFAULT_BENCHMARKS = {"INR": "^NSEI", "USD": "^GSPC"}


def currency_of(ticker: str) -> str:
    """Indian listings (.NS, .BO) trade in INR; everything else is treated as USD."""
    return "INR" if ticker.upper().endswith(INDIAN_SUFFIXES) else "USD"


def single_currency(tickers: list[str]) -> str:
    """The common currency of all tickers, or an error naming the mix.

    Converting between currencies would need FX rates and would add currency
    risk to every figure, so mixed portfolios are rejected (a documented limit).
    """
    by_currency: dict[str, list[str]] = {}
    for ticker in tickers:
        by_currency.setdefault(currency_of(ticker), []).append(ticker)
    if len(by_currency) > 1:
        detail = "; ".join(
            f"{cur}: {', '.join(names)}" for cur, names in sorted(by_currency.items())
        )
        raise InvalidPortfolioFile(
            "Mixed currencies are not supported. Upload one currency per portfolio "
            f"(Indian .NS/.BO tickers are INR, all others USD). Found {detail}.",
            {"currencies": by_currency},
        )
    return next(iter(by_currency))


def default_benchmark(currency: str) -> str:
    return DEFAULT_BENCHMARKS[currency]
