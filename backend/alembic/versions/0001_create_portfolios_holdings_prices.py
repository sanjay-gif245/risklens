"""create portfolios holdings prices

Revision ID: 0001
Revises:
Create Date: 2026-11-01 00:29:11.664349

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("benchmark", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "prices",
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("adj_close", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("ticker", "date"),
    )
    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("buy_price", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_id", "ticker"),
    )
    op.create_index(op.f("ix_holdings_portfolio_id"), "holdings", ["portfolio_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_holdings_portfolio_id"), table_name="holdings")
    op.drop_table("holdings")
    op.drop_table("prices")
    op.drop_table("portfolios")
