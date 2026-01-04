"""Routes for job applications."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlmodel import Session

from backend_api.app.core.security import get_current_user_id
from backend_api.app.db.database import get_db
from backend_api.app.db.models import ApplicationStatus, JobApplication, JobPost, User
from backend_api.app.services.notification_service import add_notification
from backend_api.app.schemas.jobs import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationRead,
    ApplicationStatusUpdate,
    JobSummary,
)


router = APIRouter(prefix="/applications", tags=["Applications"])


def _paginate(stmt, page: int, per_page: int):
    offset = (page - 1) * per_page
    return stmt.offset(offset).limit(per_page)


def _job_summary(job: JobPost) -> JobSummary:
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


def _display_name(user: Optional[User]) -> str:
    if not user:
        return "사용자"
    if user.nickname:
        return user.nickname
    if user.phone_number:
        return f"회원{user.phone_number[-4:]}"
    return "사용자"


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    me: Optional[str] = Query(None, description="'sent' 또는 'received'"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    stmt = select(JobApplication).order_by(JobApplication.applied_at.desc())

    if me == "sent":
        stmt = stmt.where(JobApplication.applicant_id == current_user_id)
    elif me == "received":
        sub = select(JobPost.id).where(JobPost.owner_id == current_user_id)
        stmt = stmt.where(
            JobApplication.job_id.in_(sub),
            JobApplication.status != ApplicationStatus.CANCELLED,
        )

    total = db.exec(select(func.count()).select_from(stmt.subquery())).scalar_one()
    applications = db.exec(_paginate(stmt, page, per_page)).scalars().all()

    items: list[ApplicationRead] = []
    for application in applications:
        job = db.get(JobPost, application.job_id)
        items.append(
            ApplicationRead(
                id=application.id,
                job_id=application.job_id,
                applicant_id=application.applicant_id,
                status=application.status,
                note=application.note,
                applied_at=application.applied_at,
                job=_job_summary(job) if job else None,
            )
        )

    has_more = page * per_page < total
    return ApplicationListResponse(items=items, page=page, per_page=per_page, total=total, has_more=has_more)


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    job = db.get(JobPost, payload.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공고를 찾을 수 없습니다.")

    existing_stmt = select(JobApplication).where(
        JobApplication.job_id == payload.job_id,
        JobApplication.applicant_id == current_user_id,
    )
    existing = db.exec(existing_stmt).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 지원한 공고입니다.")

    application = JobApplication(
        job_id=payload.job_id,
        applicant_id=current_user_id,
        note=payload.note,
        status=ApplicationStatus.PENDING,
    )

    job.applicants_count += 1

    db.add(application)
    db.add(job)

    applicant_user = db.get(User, current_user_id)
    owner_user = db.get(User, job.owner_id)
    add_notification(
        db,
        user_id=job.owner_id,
        title=f"{_display_name(applicant_user)}님이 지원했습니다",
        message=f"'{job.title}' 공고에 새 지원이 도착했습니다.",
        link=f"/matchingpage?tab=posted&job={job.id}&view=applicants",
        ntype="job_application",
    )
    add_notification(
        db,
        user_id=current_user_id,
        title="지원이 접수되었습니다",
        message=f"'{job.title}' 공고 지원이 정상적으로 접수됐어요.",
        link=f"/matchingpage?tab=applied&job={job.id}",
        ntype="application_sent",
    )

    db.commit()
    db.refresh(application)
    db.refresh(job)

    return ApplicationRead(
        id=application.id,
        job_id=application.job_id,
        applicant_id=application.applicant_id,
        status=application.status,
        note=application.note,
        applied_at=application.applied_at,
        job=_job_summary(job),
    )


@router.post("/{application_id}/status", response_model=ApplicationRead)
def update_application_status(
    application_id: UUID,
    payload: ApplicationStatusUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    application = db.get(JobApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="지원 내역을 찾을 수 없습니다.")
    job = db.get(JobPost, application.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")
    if job.owner_id != current_user_id:
        raise HTTPException(status_code=403, detail="승인 권한이 없습니다.")

    application.status = payload.status
    db.add(application)

    applicant_user = db.get(User, application.applicant_id)
    status_label = (
        "승인"
        if payload.status == ApplicationStatus.APPROVED
        else "거절"
        if payload.status == ApplicationStatus.REJECTED
        else "업데이트"
    )
    if payload.status in {ApplicationStatus.APPROVED, ApplicationStatus.REJECTED}:
        message = f"'{job.title}' 지원이 {status_label}되었습니다."
        add_notification(
            db,
            user_id=application.applicant_id,
            title=f"일자리 지원 {status_label}",
            message=message,
            link=f"/matchingpage?tab=applied&job={job.id}",
            ntype="application_result",
        )
        add_notification(
            db,
            user_id=current_user_id,
            title=f"{_display_name(applicant_user)}님 지원 {status_label}",
            message=f"'{job.title}' 공고의 지원 상태를 {status_label} 처리했습니다.",
            link=f"/matchingpage?tab=posted&job={job.id}&view=applicants",
            ntype="application_action",
        )

    db.commit()
    db.refresh(application)

    return ApplicationRead(
        id=application.id,
        job_id=application.job_id,
        applicant_id=application.applicant_id,
        status=application.status,
        note=application.note,
        applied_at=application.applied_at,
        job=_job_summary(job),
    )


@router.post("/{application_id}/cancel", response_model=ApplicationRead)
def cancel_application(
    application_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    application = db.get(JobApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="지원 내역을 찾을 수 없습니다.")
    if application.applicant_id != current_user_id:
        raise HTTPException(status_code=403, detail="취소 권한이 없습니다.")
    if application.status == ApplicationStatus.APPROVED:
        raise HTTPException(status_code=400, detail="승인된 지원은 취소할 수 없습니다.")
    if application.status == ApplicationStatus.CANCELLED:
        job = db.get(JobPost, application.job_id)
        return ApplicationRead(
            id=application.id,
            job_id=application.job_id,
            applicant_id=application.applicant_id,
            status=application.status,
            note=application.note,
            applied_at=application.applied_at,
            job=_job_summary(job) if job else None,
        )

    job = db.get(JobPost, application.job_id)
    application.status = ApplicationStatus.CANCELLED
    db.add(application)

    if job:
        if job.applicants_count > 0:
            job.applicants_count -= 1
        if job.applicants_count < 0:
            job.applicants_count = 0
        db.add(job)

    db.commit()
    db.refresh(application)
    if job:
        db.refresh(job)

    return ApplicationRead(
        id=application.id,
        job_id=application.job_id,
        applicant_id=application.applicant_id,
        status=application.status,
        note=application.note,
        applied_at=application.applied_at,
        job=_job_summary(job) if job else None,
    )
