from datetime import date

import pandas as pd
import pytest
from conftest import FIXTURE_LAST_DAY, FakePriceProvider
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Price
from app.errors import ProviderUnavailable, UnknownTickers
from app.services.data_service import DataService, missing_ranges

START = date(2021, 1, 4)


def test_missing_ranges_for_empty_cache_is_the_whole_request() -> None:
    assert missing_ranges(None, START, FIXTURE_LAST_DAY) == [(START, FIXTURE_LAST_DAY)]


def test_missing_ranges_is_empty_when_cache_covers_the_request() -> None:
    assert missing_ranges((START, FIXTURE_LAST_DAY), START, FIXTURE_LAST_DAY) == []


def test_missing_ranges_fetches_before_and_after_the_cached_bounds() -> None:
    cached = (date(2022, 1, 3), date(2022, 6, 30))
    assert missing_ranges(cached, START, date(2022, 12, 30)) == [
        (START, date(2022, 1, 2)),
        (date(2022, 7, 1), date(2022, 12, 30)),
    ]


def test_weekend_end_date_does_not_trigger_a_fetch() -> None:
    saturday = date(2023, 12, 30)
    assert missing_ranges((START, date(2023, 12, 29)), START, saturday) == []


def test_late_listing_within_a_week_of_the_start_is_not_a_gap() -> None:
    assert missing_ranges((date(2021, 1, 8), FIXTURE_LAST_DAY), START, FIXTURE_LAST_DAY) == []


def test_cold_fetch_calls_the_provider_once_and_stores_rows(
    data_service: DataService, provider: FakePriceProvider, session: Session
) -> None:
    prices = data_service.get_prices(["AAA"], START)

    assert provider.calls == [("AAA", START, FIXTURE_LAST_DAY)]
    assert len(prices["AAA"]) == 780
    assert session.scalar(select(func.count()).select_from(Price)) == 780
    assert (data_service.stats.hits, data_service.stats.misses) == (0, 1)
    assert data_service.stats.rows_fetched == 780


def test_second_request_is_served_from_the_database(
    data_service: DataService, provider: FakePriceProvider
) -> None:
    first = data_service.get_prices(["AAA", "BBB"], START)
    calls_after_first = len(provider.calls)
    second = data_service.get_prices(["AAA", "BBB"], START)

    assert len(provider.calls) == calls_after_first
    assert (data_service.stats.hits, data_service.stats.misses) == (2, 2)
    assert first["AAA"].equals(second["AAA"])


def test_asking_for_an_earlier_start_fetches_only_the_missing_head(
    data_service: DataService, provider: FakePriceProvider
) -> None:
    data_service.get_prices(["AAA"], date(2021, 6, 1))
    data_service.get_prices(["AAA"], START)

    assert provider.calls[-1] == ("AAA", START, date(2021, 5, 31))
    assert len(provider.calls) == 2


def test_a_later_day_fetches_only_the_new_tail(
    session: Session, provider: FakePriceProvider
) -> None:
    DataService(session, provider, today=lambda: date(2023, 6, 30)).get_prices(["AAA"], START)
    later = DataService(session, provider, today=lambda: FIXTURE_LAST_DAY)
    prices = later.get_prices(["AAA"], START)

    assert provider.calls[-1] == ("AAA", date(2023, 7, 1), FIXTURE_LAST_DAY)
    assert prices["AAA"].index[-1] == pd.Timestamp(FIXTURE_LAST_DAY)
    assert len(prices["AAA"]) == 780


def test_unknown_tickers_are_all_reported_together(data_service: DataService) -> None:
    with pytest.raises(UnknownTickers) as caught:
        data_service.get_prices(["AAA", "NOPE", "ALSO.NS"], START)
    assert caught.value.details == {"tickers": ["NOPE", "ALSO.NS"]}
    assert "NOPE, ALSO.NS" in caught.value.message
    assert caught.value.status_code == 422


def test_duplicate_tickers_in_one_request_are_fetched_once(
    data_service: DataService, provider: FakePriceProvider
) -> None:
    data_service.get_prices(["AAA", "AAA"], START)
    assert len(provider.calls) == 1


def test_provider_outage_surfaces_and_stores_nothing(
    session: Session, synthetic_prices: pd.DataFrame
) -> None:
    failing = FakePriceProvider(synthetic_prices, failing={"BBB"})
    service = DataService(session, failing, today=lambda: FIXTURE_LAST_DAY)
    with pytest.raises(ProviderUnavailable):
        service.get_prices(["AAA", "BBB"], START)
    assert session.scalar(select(func.count()).select_from(Price).where(Price.ticker == "BBB")) == 0
