"""Pydantic schemas for job postings, applications and AI helpers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from backend_api.app.db.models.jobs import ApplicationStatus, JobStatus


class JobBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str
    place: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    schedule: Optional[str] = None
    time: Optional[str] = None
    duration: Optional[str] = None
    requirements: Optional[str] = None
    hourly_wage: Optional[int] = Field(default=None, ge=0)
    pay_text: Optional[str] = None
    wage: Optional[str] = None
    participants: Optional[int] = Field(default=None, ge=1)
    client: Optional[str] = None
    contact: Optional[str] = None
    work_days: List[str] = Field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    images: List[str] = Field(default_factory=list)
    raw_media: List[str] = Field(default_factory=list)
    ai_confidence: Optional[float] = None
    ai_summary: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None

    @validator("lat", "lng", pre=True)
    def ensure_float(cls, value: Any) -> Optional[float]:
        if value in (None, "", "null"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class JobCreate(JobBase):
    title: str
    participants: int = Field(..., ge=1)
    hourly_wage: int = Field(..., ge=0)
    place: str
    address: str
    work_days: List[str] = Field(default_factory=list)
    start_time: str
    end_time: str
    description: str

    @validator("work_days", pre=True)
    def default_work_days(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(value)]

    @validator("images", "raw_media", pre=True)
    def ensure_list(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(value)]


class JobAiCreate(BaseModel):
    fields: Dict[str, Any]
    upload_ids: List[UUID] = Field(default_factory=list)


class JobRead(JobBase):
    id: UUID
    owner_id: UUID
    owner_name: Optional[str] = None
    owner_is_admin: bool = False
    status: JobStatus
    applicants_count: int
    views: int
    deadline: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class JobListResponse(BaseModel):
    items: List[JobRead]
    page: int
    per_page: int
    total: int
    has_more: bool


class JobSeedRequest(BaseModel):
    csv_path: Optional[str] = None
    limit: Optional[int] = None
    clear: bool = False


class JobSeedResponse(BaseModel):
    success: bool
    inserted: int
    total: int


class JobSummary(BaseModel):
    id: UUID
    title: str
    place: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    schedule: Optional[str] = None
    time: Optional[str] = None
    hourly_wage: Optional[int] = None
    wage: Optional[str] = None
    pay_text: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

    class Config:
        orm_mode = True


class JobStatusUpdate(BaseModel):
    status: JobStatus


class ApplicationCreate(BaseModel):
    job_id: UUID
    note: Optional[str] = Field(default=None, max_length=255)


class ApplicationRead(BaseModel):
    id: UUID
    job_id: UUID
    applicant_id: UUID
    status: ApplicationStatus
    note: Optional[str] = None
    applied_at: datetime
    job: Optional[JobSummary] = None

    class Config:
        orm_mode = True


class ApplicationListResponse(BaseModel):
    items: List[ApplicationRead]
    page: int
    per_page: int
    total: int
    has_more: bool


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class JobApplicantRead(BaseModel):
    id: UUID
    job_id: UUID
    applicant_id: UUID
    status: ApplicationStatus
    note: Optional[str] = None
    applied_at: datetime
    name: Optional[str] = None
    nickname: Optional[str] = None
    region: Optional[str] = None
    experience: Optional[str] = None
    match_info: Optional["ApplicantMatchInfo"] = None


class JobApplicantListResponse(BaseModel):
    items: List[JobApplicantRead]
    total: int


class MatchRead(BaseModel):
    id: UUID
    status: ApplicationStatus
    score: Optional[float] = None
    job: JobSummary


class MatchListResponse(BaseModel):
    items: List[MatchRead]
    page: int
    per_page: int
    total: int
    has_more: bool


class ApplicantMatchInfo(BaseModel):
    total_applications: int = 0
    last_applied_job: Optional[str] = None
    last_applied_at: Optional[datetime] = None
    total_matches: int = 0
    last_matched_job: Optional[str] = None
    last_matched_at: Optional[datetime] = None


JobApplicantRead.model_rebuild()


class UploadResponse(BaseModel):
    upload_ids: List[UUID]
    urls: List[str]


class OcrParseRequest(BaseModel):
    upload_ids: List[UUID]


class OcrParseResponse(BaseModel):
    raw_text: str
    cells: List[Dict[str, Any]] = Field(default_factory=list)


class AsrParseRequest(BaseModel):
    upload_ids: List[UUID]


class VoicePostRequest(BaseModel):
    upload_id: Optional[UUID] = None
    existing_post: Optional[Dict[str, Any]] = None
    clarification_text: Optional[str] = Field(default=None, max_length=5000)


class VoicePostResponse(BaseModel):
    success: bool = True
    transcript: Optional[str] = None
    post: Dict[str, Any]
    missing_fields: List[str] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    needs_clarification: bool = False
    provider: str


class MappingRequest(BaseModel):
    raw_text: str
    cells: List[Dict[str, Any]] = Field(default_factory=list)


class MappingResponse(BaseModel):
    mapped_fields: Dict[str, Any]
    confidence: float = 0.82


class MappingValidateRequest(BaseModel):
    mapped_fields: Dict[str, Any]


class MappingValidateResponse(BaseModel):
    validation_result: Dict[str, Any]
