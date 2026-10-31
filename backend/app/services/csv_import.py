"""Parse and validate an uploaded holdings CSV.

Every problem found is collected and reported at once, with its row number, so
the user can fix the file in one pass instead of one error at a time.
"""

import csv
import io
import math
import re
from dataclasses import dataclass
from typing import Any

from app.errors import InvalidPortfolioFile

REQUIRED_COLUMNS = ("ticker", "quantity", "buy_price")
TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-^=]{0,19}$")


@dataclass(frozen=True)
class HoldingInput:
    ticker: str
    quantity: float
    buy_price: float


@dataclass(frozen=True)
class ParsedHoldings:
    holdings: list[HoldingInput]
    notices: list[str]


def _problem(row: int | None, field: str | None, message: str) -> dict[str, Any]:
    return {"row": row, "field": field, "message": message}


def _positive_number(
    raw: str | None, field: str, row: int, problems: list[dict[str, Any]]
) -> float | None:
    text = (raw or "").strip()
    if not text:
        problems.append(_problem(row, field, f"{field} is empty."))
        return None
    try:
        number = float(text)
    except ValueError:
        problems.append(_problem(row, field, f"{field} '{text}' is not a number."))
        return None
    if not math.isfinite(number):
        problems.append(_problem(row, field, f"{field} '{text}' is not a finite number."))
        return None
    if number <= 0:
        problems.append(_problem(row, field, f"{field} must be greater than zero (got {text})."))
        return None
    return number


def _merge_duplicates(rows: list[tuple[int, HoldingInput]]) -> tuple[list[HoldingInput], list[str]]:
    """Combine repeated tickers: quantities add up, buy price is the quantity-weighted average.

    Merging rather than rejecting matches how a broker statement lists several lots.
    """
    merged: dict[str, HoldingInput] = {}
    notices: list[str] = []
    for _, holding in rows:
        existing = merged.get(holding.ticker)
        if existing is None:
            merged[holding.ticker] = holding
            continue
        quantity = existing.quantity + holding.quantity
        cost = existing.quantity * existing.buy_price + holding.quantity * holding.buy_price
        merged[holding.ticker] = HoldingInput(holding.ticker, quantity, cost / quantity)
        notice = f"{holding.ticker} appeared more than once; the rows were merged."
        if notice not in notices:
            notices.append(notice)
    return list(merged.values()), notices


def parse_holdings_csv(content: bytes, max_holdings: int) -> ParsedHoldings:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidPortfolioFile(
            "The file is not valid UTF-8 text. Save it as CSV (UTF-8) and upload again.",
            [_problem(None, None, "File is not UTF-8 encoded.")],
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    columns = [name.strip().lower() for name in (reader.fieldnames or [])]
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    if missing:
        raise InvalidPortfolioFile(
            f"The CSV is missing required column(s): {', '.join(missing)}. "
            f"Expected header: {', '.join(REQUIRED_COLUMNS)}.",
            [_problem(1, name, f"Column '{name}' not found.") for name in missing],
        )
    reader.fieldnames = columns

    problems: list[dict[str, Any]] = []
    rows: list[tuple[int, HoldingInput]] = []
    for row_number, record in enumerate(reader, start=2):  # row 1 is the header
        if not any((value or "").strip() for value in record.values() if isinstance(value, str)):
            continue  # blank line
        ticker = (record.get("ticker") or "").strip().upper()
        if not ticker:
            problems.append(_problem(row_number, "ticker", "ticker is empty."))
        elif not TICKER_PATTERN.match(ticker):
            problems.append(
                _problem(row_number, "ticker", f"ticker '{ticker}' is not a valid symbol.")
            )
        quantity = _positive_number(record.get("quantity"), "quantity", row_number, problems)
        buy_price = _positive_number(record.get("buy_price"), "buy_price", row_number, problems)
        if ticker and TICKER_PATTERN.match(ticker) and quantity and buy_price:
            rows.append((row_number, HoldingInput(ticker, quantity, buy_price)))

    if problems:
        count = len(problems)
        raise InvalidPortfolioFile(
            f"The CSV has {count} problem{'s' if count != 1 else ''}. Fix them and upload again.",
            problems,
        )
    if not rows:
        raise InvalidPortfolioFile(
            "The CSV has a header but no holdings.", [_problem(None, None, "No data rows found.")]
        )

    holdings, notices = _merge_duplicates(rows)
    if len(holdings) > max_holdings:
        raise InvalidPortfolioFile(
            f"The portfolio has {len(holdings)} distinct holdings; the limit is {max_holdings}.",
            [_problem(None, None, f"More than {max_holdings} holdings.")],
        )
    return ParsedHoldings(holdings, notices)
