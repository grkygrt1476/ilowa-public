"""add postgis pgvector to job_post

Revision ID: 20251202_01
Revises: 20251125_01
Create Date: 2025-12-02 20:58:21.215297

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20251202_01"
down_revision: Union[str, Sequence[str], None] = "20251125_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: enable PostGIS & pgvector."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Downgrade schema: disable PostGIS & pgvector."""
    op.execute("DROP EXTENSION IF EXISTS vector CASCADE")
    op.execute("DROP EXTENSION IF EXISTS postgis CASCADE")
