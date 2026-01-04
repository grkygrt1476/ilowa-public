"""Database models for job postings, applications and uploaded media."""


import uuid
from datetime import datetime, timezone, date
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Enum as SqlEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.types import UserDefinedType
from sqlmodel import Field, Relationship, SQLModel


class JobStatus(str, Enum):
    """Lifecycle status for a job post."""

    OPEN = "open"
    CLOSED = "closed"
    DRAFT = "draft"


class ApplicationStatus(str, Enum):
    """Application state managed by the employer."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Geometry(UserDefinedType):
    cache_ok = True

    def __init__(self, geometry_type: str = "POINT", srid: int = 4326) -> None:
        self.geometry_type = geometry_type
        self.srid = srid

    def get_col_spec(self) -> str:
        return f"geometry({self.geometry_type}, {self.srid})"


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def get_col_spec(self) -> str:
        return f"vector({self.dim})"


class JobPost(SQLModel, table=True):
    """Represents a single short-term job posting."""

    __tablename__ = "job_post"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    owner_id: uuid.UUID = Field(foreign_key="user.user_id", nullable=False, index=True)

    title: str = Field(nullable=False, max_length=200)
    description: str = Field(nullable=False)
    requirements: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None, max_length=100)

    place: Optional[str] = Field(default=None, max_length=200)
    address: Optional[str] = Field(default=None, max_length=255)
    location: Optional[str] = Field(default=None, max_length=255)
    lat: Optional[float] = Field(default=None, description="Latitude for map display")
    lng: Optional[float] = Field(default=None, description="Longitude for map display")
    geom: Optional[Any] = Field(
        default=None,
        sa_column=Column(Geometry("POINT", 4326), nullable=True),
        description="PostGIS point geometry for spatial queries",
    )
    embedding: Optional[Any] = Field(
        default=None,
        sa_column=Column(Vector(1024), nullable=True),
        description="pgvector embedding for similarity search",
    )

    schedule: Optional[str] = Field(default=None, max_length=120)
    time: Optional[str] = Field(default=None, max_length=120)
    duration: Optional[str] = Field(default=None, max_length=120)
    work_days: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
        description="List of working day codes (e.g. MON, TUE)",
    )
    start_time: Optional[str] = Field(default=None, max_length=10)
    end_time: Optional[str] = Field(default=None, max_length=10)

    participants: int = Field(default=1, ge=1)
    client: Optional[str] = Field(default=None, max_length=120)
    contact: Optional[str] = Field(default=None, max_length=40)

    hourly_wage: Optional[int] = Field(default=None, ge=0)
    pay_text: Optional[str] = Field(default=None, max_length=120)
    wage: Optional[str] = Field(default=None, max_length=120)

    status: JobStatus = Field(
        default=JobStatus.OPEN,
        sa_column=Column(SqlEnum(JobStatus, name="job_status", native_enum=False)),
    )
    applicants_count: int = Field(default=0, ge=0)
    views: int = Field(default=0, ge=0)
    deadline: Optional[date] = Field(default=None)

    images: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    raw_media: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
        description="Original uploaded files (e.g., PDF) associated with the job.",
    )

    ai_confidence: Optional[float] = Field(default=None)
    ai_summary: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )

    source: Optional[str] = Field(default=None, max_length=40)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        nullable=False,
    )

    applications: List["JobApplication"] = Relationship(
        sa_relationship=relationship(
            "JobApplication",
            back_populates="job",
        )
    )

class JobApplication(SQLModel, table=True):
    """Represents a job application submitted by a seeker."""

    __tablename__ = "job_application"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    job_id: uuid.UUID = Field(foreign_key="job_post.id", nullable=False, index=True)
    applicant_id: uuid.UUID = Field(
        foreign_key="user.user_id", nullable=False, index=True
    )

    note: Optional[str] = Field(default=None, max_length=255)
    status: ApplicationStatus = Field(
        default=ApplicationStatus.PENDING,
        sa_column=Column(
            SqlEnum(ApplicationStatus, name="application_status", native_enum=False)
        ),
    )
    applied_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    job: Optional["JobPost"] = Relationship(
        sa_relationship=relationship(
            "JobPost",
            back_populates="applications",
        )
    )

class MediaUpload(SQLModel, table=True):
    """Stores metadata for uploaded media assets."""

    __tablename__ = "media_upload"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    media_type: str = Field(nullable=False, max_length=20)
    original_name: str = Field(nullable=False, max_length=255)
    file_path: str = Field(nullable=False, max_length=500)
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )


class Notification(SQLModel, table=True):
    """User-facing notification log."""

    __tablename__ = "notification"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.user_id", nullable=False, index=True)
    type: str = Field(default="general", max_length=40)
    title: str = Field(max_length=200)
    message: str = Field(max_length=500)
    link: Optional[str] = Field(default=None, max_length=300)
    is_read: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    read_at: Optional[datetime] = Field(default=None)
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
