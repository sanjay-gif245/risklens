import pytest

from app.errors import InvalidPortfolioFile
from app.services.csv_import import ParsedHoldings, parse_holdings_csv

HEADER = "ticker,quantity,buy_price\n"


def parse(text: str, max_holdings: int = 50) -> ParsedHoldings:
    return parse_holdings_csv(text.encode("utf-8"), max_holdings)


def problems_of(text: str, max_holdings: int = 50) -> list[dict[str, object]]:
    with pytest.raises(InvalidPortfolioFile) as caught:
        parse(text, max_holdings)
    problems: list[dict[str, object]] = caught.value.details
    return problems


def test_valid_file_is_parsed_and_tickers_uppercased() -> None:
    result = parse(HEADER + "aapl, 10, 150.5\nreliance.ns,5,2500\n")
    assert [(h.ticker, h.quantity, h.buy_price) for h in result.holdings] == [
        ("AAPL", 10.0, 150.5),
        ("RELIANCE.NS", 5.0, 2500.0),
    ]
    assert result.notices == []


def test_header_is_case_insensitive_and_bom_tolerant() -> None:
    content = ("﻿Ticker, Quantity ,BUY_PRICE\nMSFT,1,300\n").encode()
    assert parse_holdings_csv(content, 50).holdings[0].ticker == "MSFT"


def test_missing_columns_are_named() -> None:
    with pytest.raises(InvalidPortfolioFile) as caught:
        parse("ticker,quantity\nAAPL,1\n")
    assert "buy_price" in caught.value.message
    assert caught.value.details == [
        {"row": 1, "field": "buy_price", "message": "Column 'buy_price' not found."}
    ]


def test_every_bad_row_is_reported_with_its_row_number() -> None:
    problems = problems_of(
        HEADER + "AAPL,abc,100\nMSFT,-5,100\nGOOG,10,0\n,1,1\nTSLA,,10\nNVDA,2,5\n"
    )
    by_row = {(p["row"], p["field"]) for p in problems}
    assert by_row == {
        (2, "quantity"),
        (3, "quantity"),
        (4, "buy_price"),
        (5, "ticker"),
        (6, "quantity"),
    }
    messages = {p["row"]: p["message"] for p in problems}
    assert "'abc' is not a number" in str(messages[2])
    assert "greater than zero" in str(messages[3])


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_non_finite_numbers_are_rejected(bad: str) -> None:
    assert problems_of(HEADER + f"AAPL,{bad},10\n")


def test_invalid_symbol_is_rejected() -> None:
    problems = problems_of(HEADER + "AA PL,1,1\n")
    assert problems[0]["field"] == "ticker"


def test_duplicate_tickers_are_merged_with_weighted_average_price() -> None:
    result = parse(HEADER + "AAPL,10,100\nMSFT,1,50\nAAPL,30,200\n")
    apple = next(h for h in result.holdings if h.ticker == "AAPL")
    assert apple.quantity == 40
    assert apple.buy_price == pytest.approx(175.0)  # (10*100 + 30*200) / 40
    assert result.notices == ["AAPL appeared more than once; the rows were merged."]
    assert len(result.holdings) == 2


def test_holding_limit_counts_distinct_tickers() -> None:
    rows = "".join(f"T{i},1,1\n" for i in range(50))
    assert len(parse(HEADER + rows).holdings) == 50
    assert len(parse(HEADER + rows + "T0,1,1\n").holdings) == 50  # a duplicate adds no holding
    too_many = problems_of(HEADER + rows + "EXTRA,1,1\n")
    assert "More than 50" in str(too_many[0]["message"])


def test_blank_lines_are_ignored() -> None:
    assert len(parse(HEADER + "AAPL,1,1\n\n,,\nMSFT,1,1\n").holdings) == 2


def test_header_only_file_is_rejected() -> None:
    assert "No data rows" in str(problems_of(HEADER)[0]["message"])


def test_empty_file_is_rejected_as_missing_columns() -> None:
    with pytest.raises(InvalidPortfolioFile, match="missing required column"):
        parse("")


def test_non_utf8_file_is_rejected() -> None:
    with pytest.raises(InvalidPortfolioFile, match="UTF-8"):
        parse_holdings_csv(b"ticker,quantity,buy_price\n\xff\xfe,1,1\n", 50)
