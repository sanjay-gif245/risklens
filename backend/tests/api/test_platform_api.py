from collections.abc import Callable, Iterator

from conftest import FakePriceProvider
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import get_session


def test_health_reports_database_status(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_is_503_when_the_database_is_down(
    make_client: Callable[[FakePriceProvider], TestClient], provider: FakePriceProvider
) -> None:
    client = make_client(provider)
    unreachable = create_engine("sqlite:////nonexistent-directory/risklens.db")

    def broken_session() -> Iterator[Session]:
        with Session(unreachable) as session:
            yield session

    client.app.dependency_overrides[get_session] = broken_session
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["code"] == "database_unavailable"


def test_unknown_route_uses_the_standard_error_shape(client: TestClient) -> None:
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Not Found", "details": None}


def test_wrong_method_uses_the_standard_error_shape(client: TestClient) -> None:
    response = client.put("/api/health")
    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"


def test_malformed_portfolio_id_is_a_validation_error(client: TestClient) -> None:
    response = client.get("/api/portfolios/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_every_response_carries_a_request_id(client: TestClient) -> None:
    assert len(client.get("/api/health").headers["X-Request-ID"]) == 12


def test_a_plain_client_supplied_request_id_is_echoed(client: TestClient) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "trace-abc.123"})
    assert response.headers["X-Request-ID"] == "trace-abc.123"


def test_an_unsafe_client_supplied_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "bad id\twith spaces"})
    assert response.headers["X-Request-ID"] != "bad id\twith spaces"


def test_cors_allows_only_the_configured_frontend_origin(client: TestClient) -> None:
    preflight = {"Access-Control-Request-Method": "POST"}
    allowed = client.options(
        "/api/portfolios", headers={"Origin": "http://localhost:5173", **preflight}
    )
    other = client.options(
        "/api/portfolios", headers={"Origin": "https://evil.example", **preflight}
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in other.headers


def test_openapi_documents_every_endpoint(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) >= {
        "/api/health",
        "/api/portfolios",
        "/api/portfolios/{portfolio_id}",
        "/api/portfolios/{portfolio_id}/risk",
        "/api/portfolios/{portfolio_id}/scenario",
        "/api/portfolios/{portfolio_id}/backtest",
        "/api/scenario-events",
    }
