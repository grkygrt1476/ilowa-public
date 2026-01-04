"""create job and media tables plus user extensions"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "20251112_01"      # ← 파일명에 맞춰 갱신
down_revision = None
branch_labels = None
depends_on = None

user_role_enum = sa.Enum("JOB_SEEKER", "EMPLOYER", "ADMIN", name="user_role", native_enum=False)
job_status_enum = sa.Enum("open", "closed", "draft", name="job_status", native_enum=False)
application_status_enum = sa.Enum(
    "pending", "approved", "rejected", name="application_status", native_enum=False
)

def upgrade() -> None:
    user_role_enum.create(op.get_bind(), checkfirst=True)
    job_status_enum.create(op.get_bind(), checkfirst=True)
    application_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user",
        sa.Column("user_id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False, unique=True),
        sa.Column("nickname", sa.String(length=20), nullable=True),
        sa.Column("location", sa.String(length=50), nullable=True),
        sa.Column("role", user_role_enum, nullable=False, server_default="JOB_SEEKER"),
        sa.Column("pin_hash", sa.String(length=255), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("preferences", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("point_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_onboarding_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "job_post",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("place", sa.String(length=200), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("schedule", sa.String(length=120), nullable=True),
        sa.Column("time", sa.String(length=120), nullable=True),
        sa.Column("duration", sa.String(length=120), nullable=True),
        sa.Column("work_days", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("start_time", sa.String(length=10), nullable=True),
        sa.Column("end_time", sa.String(length=10), nullable=True),
        sa.Column("participants", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("client", sa.String(length=120), nullable=True),
        sa.Column("contact", sa.String(length=40), nullable=True),
        sa.Column("hourly_wage", sa.Integer(), nullable=True),
        sa.Column("pay_text", sa.String(length=120), nullable=True),
        sa.Column("wage", sa.String(length=120), nullable=True),
        sa.Column("status", job_status_enum, nullable=False, server_default="open"),
        sa.Column("applicants_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("images", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("ai_summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_post_owner_id", "job_post", ["owner_id"])
    op.create_index("ix_job_post_id", "job_post", ["id"], unique=True)

    op.create_table(
        "media_upload",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("extra", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_media_upload_id", "media_upload", ["id"], unique=True)

    op.create_table(
        "job_application",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("job_post.id"), nullable=False),
        sa.Column("applicant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("status", application_status_enum, nullable=False, server_default="pending"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_application_id", "job_application", ["id"], unique=True)
    op.create_index("ix_job_application_job_id", "job_application", ["job_id"])
    op.create_index("ix_job_application_applicant_id", "job_application", ["applicant_id"])

    conn = op.get_bind()
    inspector = inspect(conn)
    if inspector.has_table("user"):
        existing_cols = {col["name"] for col in inspector.get_columns("user")}
        with op.batch_alter_table("user") as batch_op:
            if "preferences" not in existing_cols:
                batch_op.add_column(sa.Column("preferences", sa.JSON(), nullable=False, server_default="{}"))
            if "point_balance" not in existing_cols:
                batch_op.add_column(sa.Column("point_balance", sa.Integer(), nullable=False, server_default="0"))
            if "is_onboarding_complete" not in existing_cols:
                batch_op.add_column(
                    sa.Column(
                        "is_onboarding_complete",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.false(),
                    )
                )
            if "last_login" not in existing_cols:
                batch_op.add_column(sa.Column("last_login", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    if inspector.has_table("user"):
        with op.batch_alter_table("user") as batch_op:
            batch_op.drop_column("last_login")
            batch_op.drop_column("is_onboarding_complete")
            batch_op.drop_column("point_balance")
            batch_op.drop_column("preferences")

    op.drop_index("ix_job_application_applicant_id", table_name="job_application")
    op.drop_index("ix_job_application_job_id", table_name="job_application")
    op.drop_index("ix_job_application_id", table_name="job_application")
    op.drop_table("job_application")

    op.drop_index("ix_media_upload_id", table_name="media_upload")
    op.drop_table("media_upload")

    op.drop_index("ix_job_post_id", "job_post")
    op.drop_index("ix_job_post_owner_id", "job_post")
    op.drop_table("job_post")

    op.drop_table("user")

    application_status_enum.drop(op.get_bind(), checkfirst=True)
    job_status_enum.drop(op.get_bind(), checkfirst=True)
    user_role_enum.drop(op.get_bind(), checkfirst=True)
