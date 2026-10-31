"""Database tables. Types are chosen to work on both PostgreSQL and SQLite (tests)."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    base_currency: Mapped[str] = mapped_column(String(3))
    benchmark: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan", order_by="Holding.id"
    )


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("portfolio_id", "ticker"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # The index serves "all holdings of this portfolio", the only way holdings are read.
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), index=True
    )
    ticker: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[float] = mapped_column(Float)
    buy_price: Mapped[float] = mapped_column(Float)

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")


class Price(Base):
    """Cached daily adjusted close. Shared by all portfolios.

    The (ticker, date) primary key also serves the only query pattern used:
    one ticker over a date range.
    """

    __tablename__ = "prices"

    ticker: Mapped[str] = mapped_column(String(32), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    adj_close: Mapped[float] = mapped_column(Float)
