"""catalog_id as integer enum

Revision ID: c7aab0e5c716
Revises: f378b757ab54
Create Date: 2026-05-22 23:36:30.777530

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7aab0e5c716"
down_revision: str | None = "f378b757ab54"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "items",
        "catalog_id",
        existing_type=sa.VARCHAR(),
        type_=sa.Integer(),
        nullable=True,
        postgresql_using="NULLIF(catalog_id, '')::integer",
    )


def downgrade() -> None:
    op.alter_column(
        "items",
        "catalog_id",
        existing_type=sa.Integer(),
        type_=sa.VARCHAR(),
        nullable=False,
        postgresql_using="COALESCE(catalog_id::varchar, '')",
    )
