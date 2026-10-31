from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest
from conftest import FakePriceProvider
from fastapi.testclient import TestClient

CSV = "ticker,quantity,buy_price\nAAA,100,100\nBBB,200,50\nCCC,20,240\n"


def create(client: TestClient, csv_text: str = CSV) -> str:
    response = client.post(
        "/api/portfolios",
        data={"name": "Test"},
        files={"file": ("h.csv", csv_text, "text/csv")},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def risk(client: TestClient, portfolio_id: str, **params: float) -> dict[str, object]:
    response = client.get(f"/api/portfolios/{portfolio_id}/risk", params=params)
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def by_method(body: dict[str, object]) -> dict[str, dict[str, float]]:
    estimates = body["var"]
    assert isinstance(estimates, list)
    return {e["method"]: e for e in estimates}


# ---------------------------------------------------------------- risk


def test_risk_returns_every_section(client: TestClient) -> None:
    body = risk(client, create(client))
    assert set(body) >= {
        "summary",
        "var",
        "contributions",
        "correlation",
        "drawdown_curve",
        "warnings",
    }
    assert body["confidence"] == 0.95
    assert body["horizon_days"] == 1
    assert body["observations"] == 779
    assert body["benchmark"] == "^GSPC"
    assert set(by_method(body)) == {"historical", "parametric", "monte_carlo"}


def test_contributions_add_up_to_portfolio_volatility(client: TestClient) -> None:
    body = risk(client, create(client))
    contributions = body["contributions"]
    summary = body["summary"]
    assert isinstance(contributions, list) and isinstance(summary, dict)
    assert sum(c["contribution"] for c in contributions) == pytest.approx(
        summary["annual_volatility"]
    )
    assert sum(c["pct_contribution"] for c in contributions) == pytest.approx(1.0)
    assert sum(c["weight"] for c in contributions) == pytest.approx(1.0)


def test_var_amount_is_percentage_times_portfolio_value(client: TestClient) -> None:
    body = risk(client, create(client))
    value = body["portfolio_value"]
    assert isinstance(value, float)
    for estimate in by_method(body).values():
        assert estimate["var_amount"] == pytest.approx(estimate["var_pct"] * value)
    historical = by_method(body)["historical"]
    assert historical["cvar_amount"] == pytest.approx(historical["cvar_pct"] * value)


def test_higher_confidence_means_larger_var_and_cvar_exceeds_var(client: TestClient) -> None:
    portfolio_id = create(client)
    at_95 = by_method(risk(client, portfolio_id, confidence=0.95))
    at_99 = by_method(risk(client, portfolio_id, confidence=0.99))
    for method in at_95:
        assert at_99[method]["var_pct"] >= at_95[method]["var_pct"]
    for method in ("historical", "monte_carlo"):
        assert at_95[method]["cvar_pct"] >= at_95[method]["var_pct"]
    assert at_95["parametric"]["cvar_pct"] is None


def test_monte_carlo_agrees_with_parametric(client: TestClient) -> None:
    estimates = by_method(risk(client, create(client)))
    assert estimates["monte_carlo"]["var_pct"] == pytest.approx(
        estimates["parametric"]["var_pct"], rel=0.05
    )


def test_horizon_scales_by_square_root_of_time(client: TestClient) -> None:
    portfolio_id = create(client)
    one = by_method(risk(client, portfolio_id, horizon=1))
    ten = by_method(risk(client, portfolio_id, horizon=10))
    assert ten["historical"]["var_pct"] == pytest.approx(one["historical"]["var_pct"] * 10**0.5)


def test_lookback_limits_the_sample(client: TestClient) -> None:
    portfolio_id = create(client)
    body = risk(client, portfolio_id, lookback=100)
    assert body["observations"] == 100
    assert body["warnings"] == []


def test_lookback_longer_than_the_history_is_capped_with_a_warning(client: TestClient) -> None:
    body = risk(client, create(client), lookback=2000)
    assert body["observations"] == 779
    warnings = body["warnings"]
    assert isinstance(warnings, list) and "reduced" in warnings[0]


def test_summary_metrics_are_sensible(client: TestClient) -> None:
    summary = risk(client, create(client))["summary"]
    assert isinstance(summary, dict)
    assert 0 < summary["annual_volatility"] < 1
    assert 0 < summary["max_drawdown"]["depth"] < 1
    assert summary["max_drawdown"]["peak_date"] < summary["max_drawdown"]["trough_date"]
    assert -1 <= summary["correlation_to_benchmark"] <= 1
    assert summary["beta"] > 0
    assert summary["risk_free_rate"] == 0.04
    expected_sharpe = (summary["annual_return"] - 0.04) / summary["annual_volatility"]
    assert summary["sharpe_ratio"] == pytest.approx(expected_sharpe)


def test_indian_portfolio_uses_the_inr_risk_free_rate(client: TestClient) -> None:
    portfolio_id = create(client, "ticker,quantity,buy_price\nRELI.NS,10,1900\nTCSX.NS,5,3100\n")
    summary = risk(client, portfolio_id)["summary"]
    assert isinstance(summary, dict)
    assert summary["risk_free_rate"] == 0.065


def test_correlation_matrix_is_symmetric_with_unit_diagonal(client: TestClient) -> None:
    correlation = risk(client, create(client))["correlation"]
    assert isinstance(correlation, dict)
    matrix = np.array(correlation["matrix"])
    assert correlation["tickers"] == ["AAA", "BBB", "CCC"]
    assert np.allclose(np.diag(matrix), 1.0)
    assert np.allclose(matrix, matrix.T)


def test_drawdown_curve_is_never_positive_and_covers_the_sample(client: TestClient) -> None:
    curve = risk(client, create(client))["drawdown_curve"]
    assert isinstance(curve, list)
    assert len(curve) == 779
    assert max(point["drawdown"] for point in curve) <= 1e-12


def test_short_history_holding_is_excluded_and_reported(client: TestClient) -> None:
    body = risk(client, create(client, "ticker,quantity,buy_price\nAAA,10,100\nNEWCO,10,30\n"))
    assert body["excluded"] == {"NEWCO": 120}
    warnings = body["warnings"]
    assert isinstance(warnings, list) and "NEWCO excluded" in warnings[0]
    contributions = body["contributions"]
    assert isinstance(contributions, list) and [c["ticker"] for c in contributions] == ["AAA"]


def test_single_stock_portfolio_works(client: TestClient) -> None:
    body = risk(client, create(client, "ticker,quantity,buy_price\nAAA,10,100\n"))
    contributions = body["contributions"]
    assert isinstance(contributions, list)
    assert contributions[0]["pct_contribution"] == pytest.approx(1.0)


def test_portfolio_without_any_usable_history_is_a_clear_422(client: TestClient) -> None:
    portfolio_id = create(client, "ticker,quantity,buy_price\nNEWCO,10,30\n")
    response = client.get(f"/api/portfolios/{portfolio_id}/risk")
    assert response.status_code == 422
    assert response.json()["code"] == "insufficient_data"


@pytest.mark.parametrize(
    "params",
    [{"confidence": 0.5}, {"confidence": 1.0}, {"horizon": 0}, {"horizon": 31}, {"lookback": 5}],
)
def test_out_of_range_parameters_are_rejected(client: TestClient, params: dict[str, float]) -> None:
    response = client.get(f"/api/portfolios/{create(client)}/risk", params=params)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# ----------------------------------------------------------- scenarios


def scenario(client: TestClient, portfolio_id: str, body: dict[str, object]) -> dict[str, object]:
    response = client.post(f"/api/portfolios/{portfolio_id}/scenario", json=body)
    assert response.status_code == 200, response.text
    result: dict[str, object] = response.json()
    return result


def test_market_shock_equals_portfolio_beta_times_the_move(client: TestClient) -> None:
    portfolio_id = create(client)
    beta = risk(client, portfolio_id)["summary"]["beta"]
    result = scenario(client, portfolio_id, {"type": "market_shock", "benchmark_move": -0.10})
    assert result["pnl_pct"] == pytest.approx(beta * -0.10)
    assert result["pnl"] == pytest.approx(result["pnl_pct"] * result["total_value"])
    notes = result["notes"]
    assert isinstance(notes, list) and "Single-factor" in notes[-1]


def test_custom_shocks_touch_only_the_named_tickers(client: TestClient) -> None:
    result = scenario(client, create(client), {"type": "custom_shocks", "shocks": {"AAA": -0.5}})
    holdings = {h["ticker"]: h for h in result["holdings"]}
    assert holdings["AAA"]["pnl"] == pytest.approx(-0.5 * holdings["AAA"]["value"])
    assert holdings["BBB"]["pnl"] == 0
    assert result["pnl"] == pytest.approx(holdings["AAA"]["pnl"])


def test_custom_shock_for_a_ticker_not_held_is_rejected(client: TestClient) -> None:
    response = client.post(
        f"/api/portfolios/{create(client)}/scenario",
        json={"type": "custom_shocks", "shocks": {"ZZZ": -0.1}},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_historical_replay_matches_a_manual_calculation(
    client: TestClient, synthetic_prices: pd.DataFrame
) -> None:
    portfolio_id = create(client)
    start, end = synthetic_prices.index[598], synthetic_prices.index[621]
    result = scenario(
        client,
        portfolio_id,
        {"type": "historical_replay", "start_date": str(start.date()), "end_date": str(end.date())},
    )

    quantities = {"AAA": 100, "BBB": 200, "CCC": 20}
    last = synthetic_prices.iloc[-1]
    expected_pnl = sum(
        quantities[t]
        * last[t]
        * (synthetic_prices.loc[end, t] / synthetic_prices.loc[start, t] - 1)
        for t in quantities
    )
    assert result["pnl"] == pytest.approx(expected_pnl)
    assert result["pnl_pct"] < 0  # the fixture's stress episode sits in this window
    path = result["path"]
    assert isinstance(path, list)
    assert path[0]["change"] == pytest.approx(0.0)
    assert path[-1]["change"] == pytest.approx(result["pnl_pct"])
    assert result["start_date"] == str(start.date())


def test_replay_marks_holdings_that_did_not_exist_and_covers_the_rest(
    make_client: Callable[[FakePriceProvider], TestClient], synthetic_prices: pd.DataFrame
) -> None:
    prices = synthetic_prices[["AAA", "^GSPC"]].copy()
    prices["LATE"] = prices["AAA"] * 0.5
    prices.loc[prices.index[:380], "LATE"] = np.nan
    client = make_client(FakePriceProvider(prices))
    portfolio_id = create(client, "ticker,quantity,buy_price\nAAA,10,100\nLATE,10,50\n")

    result = scenario(
        client,
        portfolio_id,
        {
            "type": "historical_replay",
            "start_date": str(prices.index[20].date()),
            "end_date": str(prices.index[80].date()),
        },
    )
    holdings = {h["ticker"]: h for h in result["holdings"]}
    assert holdings["AAA"]["covered"] is True
    assert holdings["LATE"]["covered"] is False
    assert result["covered_value"] == pytest.approx(holdings["AAA"]["value"])
    notes = result["notes"]
    assert isinstance(notes, list) and "LATE did not trade" in notes[0]


def test_replay_of_a_window_before_any_data_is_a_clear_422(client: TestClient) -> None:
    response = client.post(
        f"/api/portfolios/{create(client)}/scenario",
        json={"type": "historical_replay", "event": "covid_crash_2020"},
    )
    assert response.status_code == 422
    assert "None of the holdings has prices" in response.json()["message"]


@pytest.mark.parametrize(
    "body",
    [
        {"type": "mystery"},
        {"type": "market_shock", "benchmark_move": -2},
        {"type": "custom_shocks", "shocks": {}},
        {"type": "historical_replay"},
        {
            "type": "historical_replay",
            "event": "x",
            "start_date": "2020-01-01",
            "end_date": "2020-02-01",
        },
    ],
)
def test_malformed_scenario_requests_are_rejected(
    client: TestClient, body: dict[str, object]
) -> None:
    response = client.post(f"/api/portfolios/{create(client)}/scenario", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.parametrize(
    ("body", "fragment"),
    [
        ({"type": "historical_replay", "event": "made_up"}, "Unknown event"),
        (
            {"type": "historical_replay", "start_date": "2023-06-01", "end_date": "2023-06-03"},
            "at least 5 days",
        ),
        (
            {"type": "historical_replay", "start_date": "2023-06-01", "end_date": "2024-06-01"},
            "future",
        ),
    ],
)
def test_unusable_replay_windows_are_explained(
    client: TestClient, body: dict[str, object], fragment: str
) -> None:
    response = client.post(f"/api/portfolios/{create(client)}/scenario", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
    assert fragment in response.json()["message"]


def test_scenario_events_are_listed(client: TestClient) -> None:
    events = client.get("/api/scenario-events").json()
    assert [e["key"] for e in events] == [
        "covid_crash_2020",
        "financial_crisis_2008",
        "rate_shock_2022",
    ]
    assert events[0]["start_date"] == "2020-02-19"


# ------------------------------------------------------------ backtest


def backtest(client: TestClient, portfolio_id: str, **params: int) -> dict[str, object]:
    response = client.get(f"/api/portfolios/{portfolio_id}/backtest", params=params)
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def test_backtest_covers_three_methods_at_two_confidence_levels(client: TestClient) -> None:
    body = backtest(client, create(client))
    results = body["results"]
    dates = body["dates"]
    assert isinstance(results, list) and isinstance(dates, list)
    assert [(r["method"], r["confidence"]) for r in results] == [
        (method, confidence)
        for confidence in (0.95, 0.99)
        for method in ("historical", "parametric", "monte_carlo")
    ]
    assert len(dates) == 779 - 250 == len(body["realized_returns"])
    assert body["window"] == 250


def test_backtest_results_are_internally_consistent(client: TestClient) -> None:
    body = backtest(client, create(client))
    dates = set(body["dates"])
    for result in body["results"]:
        assert len(result["var"]) == len(body["dates"])
        assert result["breaches"] == len(result["breach_dates"])
        assert set(result["breach_dates"]) <= dates
        assert result["observed_rate"] == pytest.approx(result["breaches"] / result["observations"])
        assert result["expected_rate"] == pytest.approx(1 - result["confidence"])
        assert 0 <= result["p_value"] <= 1
        assert result["rejected"] == (result["p_value"] < 0.05)
        assert result["verdict"].startswith(
            "Model rejected" if result["rejected"] else "Model accepted"
        )
        assert all(v > 0 for v in result["var"])


def test_breaches_are_days_where_the_loss_exceeded_var(client: TestClient) -> None:
    body = backtest(client, create(client))
    realized = dict(zip(body["dates"], body["realized_returns"], strict=True))
    for result in body["results"]:
        by_date = dict(zip(body["dates"], result["var"], strict=True))
        expected = [d for d in realized if realized[d] < -by_date[d]]
        assert result["breach_dates"] == expected


def test_a_shorter_estimation_window_gives_more_test_days(client: TestClient) -> None:
    body = backtest(client, create(client), window=120)
    assert len(body["dates"]) == 779 - 120
    assert body["window"] == 120


def test_low_power_at_99_percent_is_flagged(client: TestClient) -> None:
    body = backtest(client, create(client), window=300)
    warnings = body["warnings"]
    assert isinstance(warnings, list)
    assert any("99%" in w and "little power" in w for w in warnings)


def test_backtest_needs_history_beyond_the_window(client: TestClient) -> None:
    response = client.get(f"/api/portfolios/{create(client)}/backtest", params={"window": 750})
    assert response.status_code == 422
    assert response.json()["code"] == "insufficient_data"


def test_backtest_window_below_the_minimum_is_rejected(client: TestClient) -> None:
    response = client.get(f"/api/portfolios/{create(client)}/backtest", params={"window": 10})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
