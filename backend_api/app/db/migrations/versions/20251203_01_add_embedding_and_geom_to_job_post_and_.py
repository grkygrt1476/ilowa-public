"""add embedding_and_geom_to_job_post_and_users

Revision ID: 20251203_01
Revises: 20251202_01
Create Date: 2025-12-03 15:37:04.053519

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "20251203_01"
down_revision: Union[str, Sequence[str], None] = "20251202_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add geom & embedding columns and indexes."""

    conn = op.get_bind()
    inspector = inspect(conn)

    # 1) job_post: 위치+벡터
    op.execute(
        """
        ALTER TABLE job_post
        ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326),
        ADD COLUMN IF NOT EXISTS embedding vector(1024);
        """
    )

    # 2) job_post 인덱스 (공간 + 벡터)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_job_post_geom
        ON job_post
        USING gist (geom);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_job_post_embedding
        ON job_post
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
    )

    # 3) users: 취향 embedding (users 테이블이 있을 때만 수행)
    if inspector.has_table("users"):
        op.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS embedding vector(1024);
            """
        )

        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_users_embedding
            ON users
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """
        )

    # 4) 기존 lat/lon → geom 백필
    job_post_cols = {col["name"] for col in inspector.get_columns("job_post")}
    if {"lat", "lng"}.issubset(job_post_cols):
        op.execute(
            """
            UPDATE job_post
            SET geom = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
            WHERE geom IS NULL
              AND lat IS NOT NULL
              AND lng IS NOT NULL;
            """
        )


def downgrade() -> None:
    """Drop indexes & columns."""

    # 역순으로 지우기
    op.execute("DROP INDEX IF EXISTS idx_users_embedding;")
    op.execute("DROP INDEX IF EXISTS idx_job_post_embedding;")
    op.execute("DROP INDEX IF EXISTS idx_job_post_geom;")

    conn = op.get_bind()
    inspector = inspect(conn)
    if inspector.has_table("users"):
        op.execute(
            """
            ALTER TABLE users
            DROP COLUMN IF EXISTS embedding;
            """
        )

    op.execute(
        """
        ALTER TABLE job_post
        DROP COLUMN IF EXISTS embedding,
        DROP COLUMN IF EXISTS geom;
        """
    )
