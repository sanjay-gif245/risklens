import uuid
from collections.abc import Callable

import pandas as pd
import pytest
from conftest import FakePriceProvider
from fastapi.testclient import TestClient
from httpx import Response

from app.services import portfolio_service

HEADER = "ticker,quantity,buy_price\n"
US_CSV = HEADER + "AAA,100,100\nBBB,200,50\nCCC,20,240\n"


def upload(
    client: TestClient, csv_text: str = US_CSV, name: str = "Growth", benchmark: str | None = None
) -> Response:
    data = {"name": name}
    if benchmark is not None:
        data["benchmark"] = benchmark
    return client.post(
        "/api/portfolios", data=data, files={"file": ("holdings.csv", csv_text, "text/csv")}
    )


def test_upload_creates_a_portfolio_with_current_values(client: TestClient) -> None:
    response = upload(client)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Growth"
    assert body["base_currency"] == "USD"
    assert body["benchmark"] == "^GSPC"
    assert body["as_of"] == "2023-12-29"
    assert [h["ticker"] for h in body["holdings"]] == ["AAA", "BBB", "CCC"]
    assert sum(h["weight"] for h in body["holdings"]) == pytest.approx(1.0)
    first = body["holdings"][0]
    assert first["market_value"] == pytest.approx(first["quantity"] * first["last_price"])
    assert first["unrealized_pnl"] == pytest.approx(first["market_value"] - first["cost_value"])
    assert body["total_value"] == pytest.approx(sum(h["market_value"] for h in body["holdings"]))
    assert body["warnings"] == []


def test_upload_reports_merged_duplicate_rows(client: TestClient) -> None:
    body = upload(client, HEADER + "AAA,10,100\nBBB,5,50\nAAA,10,120\n").json()
    assert body["notices"] == ["AAA appeared more than once; the rows were merged."]
    assert len(body["holdings"]) == 2
    assert body["holdings"][0]["buy_price"] == pytest.approx(110.0)


def test_upload_flags_holdings_with_too_little_history(client: TestClient) -> None:
    body = upload(client, HEADER + "AAA,10,100\nNEWCO,10,30\n").json()
    newco = next(h for h in body["holdings"] if h["ticker"] == "NEWCO")
    assert newco["analysed"] is False
    assert newco["history_days"] == 120
    assert "NEWCO excluded" in body["warnings"][0]


def test_list_get_and_delete(client: TestClient) -> None:
    created = upload(client).json()
    upload(client, name="Second")

    listing = client.get("/api/portfolios").json()
    assert {p["name"] for p in listing} == {"Growth", "Second"}
    assert all(p["holding_count"] == 3 for p in listing)

    fetched = client.get(f"/api/portfolios/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["total_value"] == pytest.approx(created["total_value"])

    assert client.delete(f"/api/portfolios/{created['id']}").status_code == 204
    gone = client.get(f"/api/portfolios/{created['id']}")
    assert gone.status_code == 404
    assert gone.json()["code"] == "portfolio_not_found"
    assert len(client.get("/api/portfolios").json()) == 1


def test_unknown_portfolio_returns_the_standard_error_shape(client: TestClient) -> None:
    response = client.get(f"/api/portfolios/{uuid.uuid4()}")
    assert response.status_code == 404
    assert set(response.json()) == {"code", "message", "details"}


def test_invalid_csv_lists_every_problem_with_its_row(client: TestClient) -> None:
    response = upload(client, HEADER + "AAA,abc,100\nBBB,-1,50\n")
    body = response.json()
    assert response.status_code == 422
    assert body["code"] == "invalid_portfolio_file"
    assert [(d["row"], d["field"]) for d in body["details"]] == [(2, "quantity"), (3, "quantity")]


def test_missing_column_is_rejected_by_name(client: TestClient) -> None:
    body = upload(client, "ticker,quantity\nAAA,1\n").json()
    assert "buy_price" in body["message"]


def test_unknown_ticker_is_rejected_and_nothing_is_stored(client: TestClient) -> None:
    response = upload(client, HEADER + "AAA,1,1\nNOPE,1,1\n")
    assert response.status_code == 422
    assert response.json()["code"] == "unknown_ticker"
    assert response.json()["details"] == {"tickers": ["NOPE"]}
    assert client.get("/api/portfolios").json() == []


def test_mixed_currencies_are_rejected(client: TestClient) -> None:
    response = upload(client, HEADER + "AAA,1,1\nRELI.NS,1,1\n")
    assert response.status_code == 422
    assert "Mixed currencies" in response.json()["message"]


def test_indian_portfolio_uses_inr_and_nifty(client: TestClient) -> None:
    body = upload(client, HEADER + "RELI.NS,10,1900\nTCSX.NS,5,3100\n").json()
    assert (body["base_currency"], body["benchmark"]) == ("INR", "^NSEI")


def test_benchmark_can_be_overridden(client: TestClient) -> None:
    assert upload(client, benchmark="^nsei").json()["benchmark"] == "^NSEI"


def test_oversized_upload_is_rejected(client: TestClient) -> None:
    response = upload(client, HEADER + "A" * 1_100_000)
    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"


def test_missing_form_field_is_a_validation_error_with_field_names(client: TestClient) -> None:
    response = client.post("/api/portfolios", files={"file": ("h.csv", US_CSV, "text/csv")})
    body = response.json()
    assert response.status_code == 422
    assert body["code"] == "validation_error"
    assert any("name" in detail["field"] for detail in body["details"])


def test_provider_outage_during_upload_is_a_502_not_a_crash(
    make_client: Callable[[FakePriceProvider], TestClient], synthetic_prices: pd.DataFrame
) -> None:
    broken = FakePriceProvider(synthetic_prices, failing={"BBB"})
    response = upload(make_client(broken))
    assert response.status_code == 502
    assert response.json()["code"] == "price_provider_unavailable"


def test_unexpected_errors_become_a_500_with_a_request_id(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(session: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(portfolio_service, "list_portfolios", explode)
    response = client.get("/api/portfolios")
    body = response.json()
    assert response.status_code == 500
    assert body["code"] == "internal_error"
    assert response.headers["X-Request-ID"] in body["message"]
    assert "boom" not in response.text  # internals are not leaked
