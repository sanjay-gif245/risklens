import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile

from app.api.deps import DataDep, SessionDep
from app.config import get_settings
from app.errors import FileTooLarge
from app.schemas.portfolio import PortfolioDetail, PortfolioSummary
from app.services import portfolio_service
from app.services.csv_import import parse_holdings_csv

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("", status_code=201, response_model=PortfolioDetail)
def create_portfolio(
    session: SessionDep,
    data: DataDep,
    file: Annotated[UploadFile, File(description="CSV with columns ticker, quantity, buy_price")],
    name: Annotated[str, Form()],
    benchmark: Annotated[str | None, Form()] = None,
) -> PortfolioDetail:
    """Upload a holdings CSV. Every ticker is checked against real price data."""
    settings = get_settings()
    content = file.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise FileTooLarge(f"The file is larger than {settings.max_upload_bytes // 1000} KB.")
    parsed = parse_holdings_csv(content, settings.max_holdings)
    portfolio = portfolio_service.create_portfolio(session, data, name, parsed, benchmark)
    return portfolio_service.describe_portfolio(portfolio, data, parsed.notices)


@router.get("", response_model=list[PortfolioSummary])
def list_portfolios(session: SessionDep) -> list[PortfolioSummary]:
    return [portfolio_service.summarise(p) for p in portfolio_service.list_portfolios(session)]


@router.get("/{portfolio_id}", response_model=PortfolioDetail)
def get_portfolio(portfolio_id: uuid.UUID, session: SessionDep, data: DataDep) -> PortfolioDetail:
    portfolio = portfolio_service.get_portfolio(session, portfolio_id)
    return portfolio_service.describe_portfolio(portfolio, data)


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(portfolio_id: uuid.UUID, session: SessionDep) -> Response:
    portfolio_service.delete_portfolio(session, portfolio_id)
    return Response(status_code=204)
