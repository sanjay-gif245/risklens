"""Dependencies shared by the routers. Tests replace these with fakes."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_session
from app.services.data_service import DataService
from app.services.price_provider import PriceProvider, YFinanceProvider


def get_price_provider() -> PriceProvider:
    settings = get_settings()
    return YFinanceProvider(settings.provider_attempts, settings.provider_backoff_seconds)


def get_data_service(
    session: Annotated[Session, Depends(get_session)],
    provider: Annotated[PriceProvider, Depends(get_price_provider)],
) -> DataService:
    return DataService(session, provider)


SessionDep = Annotated[Session, Depends(get_session)]
DataDep = Annotated[DataService, Depends(get_data_service)]
