from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import SessionDep
from app.errors import DatabaseUnavailable

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=HealthResponse)
def health(session: SessionDep) -> HealthResponse:
    """Liveness plus a database round trip, used by the hosting health check."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise DatabaseUnavailable("The database is not reachable.") from exc
    return HealthResponse(status="ok", database="ok")
