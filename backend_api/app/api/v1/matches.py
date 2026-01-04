"""Routes for match history built from approved applications."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlmodel import Session

from backend_api.app.core.security import get_current_user_id
from backend_api.app.db.database import get_db
from backend_api.app.db.models import ApplicationStatus, JobApplication, JobPost
from backend_api.app.schemas.jobs import MatchListResponse, MatchRead, JobSummary


router = APIRouter(prefix="/matches", tags=["Matches"])


def _paginate(stmt, page: int, per_page: int):
    offset = (page - 1) * per_page
    return stmt.offset(offset).limit(per_page)


def _summary(job: JobPost) -> JobSummary:
    return JobSummary(
        id=job.id,
        title=job.title,
        place=job.place,
        location=job.location,
        address=job.address,
        schedule=job.schedule,
        time=job.time,
        hourly_wage=job.hourly_wage,
        wage=job.wage,
        pay_text=job.pay_text,
        lat=job.lat,
        lng=job.lng,
    )


@router.get("", response_model=MatchListResponse)
def list_matches(
    me: Optional[str] = Query("all"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    stmt = select(JobApplication).where(JobApplication.status == ApplicationStatus.APPROVED)

    if me == "sent":
        stmt = stmt.where(JobApplication.applicant_id == current_user_id)
    elif me == "received":
        sub = select(JobPost.id).where(JobPost.owner_id == current_user_id)
        stmt = stmt.where(JobApplication.job_id.in_(sub))
    else:
        sub = select(JobPost.id).where(JobPost.owner_id == current_user_id)
        stmt = stmt.where(
            (JobApplication.applicant_id == current_user_id)
            | (JobApplication.job_id.in_(sub))
        )

    stmt = stmt.order_by(JobApplication.applied_at.desc())

    total = db.exec(select(func.count()).select_from(stmt.subquery())).scalar_one()
    applications = db.exec(_paginate(stmt, page, per_page)).scalars().all()

    items: list[MatchRead] = []
    for application in applications:
        job = db.get(JobPost, application.job_id)
        if not job:
            continue
        items.append(
            MatchRead(
                id=application.id,
                status=application.status,
                job=_summary(job),
            )
        )

    has_more = page * per_page < total

    return MatchListResponse(items=items, page=page, per_page=per_page, total=total, has_more=has_more)
