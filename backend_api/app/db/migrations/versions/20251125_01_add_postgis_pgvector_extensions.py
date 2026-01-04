"""add postgis and pgvector extensions

Revision ID: 20251125_01
Revises: 20251112_01
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251125_01"
down_revision = "20251112_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    pass
