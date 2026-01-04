"""add raw_media column to job_post

Revision ID: 20251125_02
Revises: 20251125_01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251125_02"
down_revision = "20251125_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_post",
        sa.Column("raw_media", sa.JSON(), nullable=False, server_default="[]"),
    )



def downgrade() -> None:
    op.drop_column("job_post", "raw_media")
