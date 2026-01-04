"""Routes for managing job postings."""

from __future__ import annotations

import logging
import math
import os
import pathlib

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, or_
from sqlmodel import Session

from backend_api.app.core.security import get_current_user_id
from backend_api.app.db.database import get_db
from backend_api.app.db.models import (
    ApplicationStatus,
    JobApplication,
    JobPost,
    JobStatus,
    MediaUpload,
    User,
    UserRole,
)
from backend_api.app.services.naver_geocoder import NaverGeocoder
from backend_api.app.services.google_geocoder import GoogleGeocoder
from backend_api.app.services.job_seeder import seed_jobs_from_csv
from backend_api.app.services.ai_pipeline import get_pipeline
from backend_api.app.schemas.jobs import (
    ApplicantMatchInfo,
    JobAiCreate,
    JobApplicantListResponse,
    JobApplicantRead,
    JobCreate,
    JobListResponse,
    JobRead,
    JobSeedRequest,
    JobSeedResponse,
    JobStatusUpdate,
)
from ai_modeling.schemas.recommendation import UserProfile


router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = logging.getLogger(__name__)
DEFAULT_COORDS = (37.5665, 126.9780)
DEFAULT_SEED_CSV = pathlib.Path(
    os.getenv(
        "SEED_JOBS_JSON",
        os.getenv("SEED_JOBS_CSV", "ai_modeling/data_samples/demo_jobs_50.json"),
    )
)
logger.info("Job seed CSV path resolved to %s", DEFAULT_SEED_CSV)
_NAVER_GEOCODER: Optional[NaverGeocoder] = None
_NAVER_GEOCODER_DISABLED = False
_NAVER_GEOCODER_CACHE = pathlib.Path(
    os.getenv("NAVER_GEOCODER_CACHE", ".naver_geocode_cache_api.json")
)
_GOOGLE_GEOCODER: Optional[GoogleGeocoder] = None
_GOOGLE_GEOCODER_DISABLED = False
_GOOGLE_GEOCODER_CACHE = pathlib.Path(
    os.getenv("GOOGLE_GEOCODER_CACHE", ".google_geocode_cache_api.json")
)


def _paginate(stmt, page: int, per_page: int):
    offset = (page - 1) * per_page
    return stmt.offset(offset).limit(per_page)


def _coerce_uuid(value: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:  # pragma: no cover - FastAPI converts validation errors
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 공고입니다.") from exc


def _get_naver_geocoder() -> Optional[NaverGeocoder]:
    global _NAVER_GEOCODER, _NAVER_GEOCODER_DISABLED
    if _NAVER_GEOCODER_DISABLED:
        return None
    if _NAVER_GEOCODER is None:
        try:
            _NAVER_GEOCODER = NaverGeocoder(cache_path=_NAVER_GEOCODER_CACHE)
            logger.info(
                "Naver geocoder enabled for job coordinates using cache %s",
                _NAVER_GEOCODER_CACHE,
            )
        except Exception as exc:  # pragma: no cover - depends on env
            _NAVER_GEOCODER_DISABLED = True
            logger.warning("Naver geocoder disabled: %s", exc)
            return None
    return _NAVER_GEOCODER


def _get_google_geocoder() -> Optional[GoogleGeocoder]:
    global _GOOGLE_GEOCODER, _GOOGLE_GEOCODER_DISABLED
    if _GOOGLE_GEOCODER_DISABLED:
        return None
    if _GOOGLE_GEOCODER is None:
        try:
            _GOOGLE_GEOCODER = GoogleGeocoder(cache_path=_GOOGLE_GEOCODER_CACHE)
            logger.info(
                "Google geocoder enabled for job coordinates using cache %s",
                _GOOGLE_GEOCODER_CACHE,
            )
        except Exception as exc:
            _GOOGLE_GEOCODER_DISABLED = True
            logger.warning("Google geocoder disabled: %s", exc)
            return None
    return _GOOGLE_GEOCODER


def _build_user_profile(user: User) -> UserProfile:
    prefs = user.preferences or {}
    regions = prefs.get("regions") or []
    if not regions and user.location:
        regions = [user.location]
    return UserProfile(
        nickname=user.nickname or user.phone_number or "회원",
        regions=regions,
        days=prefs.get("days") or [],
        time_slots=prefs.get("time_slots") or [],
        experiences=prefs.get("experiences") or [],
        capabilities=prefs.get("capabilities") or {},
    )


def _guess_coordinates(*candidates: Optional[str]) -> tuple[Optional[float], Optional[float]]:
    texts = [text.strip() for text in candidates if text and text.strip()]
    if not texts:
        return DEFAULT_COORDS

    geocoder = _get_naver_geocoder()
    if geocoder:
        # Try individual candidates first, then the combined text for better accuracy.
        queries = texts + [" ".join(texts)]
        for query in queries:
            if not query:
                continue
            try:
                coords = geocoder.geocode(query)
            except Exception as exc:  # pragma: no cover - network issues
                logger.warning("Naver geocode failed for '%s': %s", query, exc)
                coords = None
            if coords:
                return coords

    google = _get_google_geocoder()
    if google:
        for query in texts + [" ".join(texts)]:
            if not query:
                continue
            try:
                coords = google.geocode(query)
            except Exception as exc:
                logger.warning("Google geocode failed for '%s': %s", query, exc)
                coords = None
            if coords:
                return coords

    mapping = {
        "성동": (37.5636, 127.0364),
        "강남": (37.5172, 127.0473),
        "서초": (37.4836, 127.0327),
        "마포": (37.5568, 126.9101),
        "송파": (37.5145, 127.1056),
        "은평": (37.6176, 126.9227),
        "부산": (35.1796, 129.0756),
        "대구": (35.8714, 128.6014),
        "광주": (35.1595, 126.8526),
        "대전": (36.3504, 127.3845),
    }

    for query in texts:
        for key, coords in mapping.items():
            if key in query:
                return coords

    return DEFAULT_COORDS


def _coerce_float(value: Any) -> Optional[float]:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    if phone is None:
        return None
    digits = phone.replace("-", "").strip()
    return digits or None


def _admin_phone_candidates() -> set[str]:
    default_candidates = {"01000000000", "010-0000-0000"}
    env_phone = os.getenv("ADMIN_PHONE")
    if env_phone:
        default_candidates.add(env_phone)
    env_aliases = os.getenv("ADMIN_PHONE_ALIASES", "")
    for entry in env_aliases.split(","):
        if entry.strip():
            default_candidates.add(entry.strip())
    normalized = {
        normalized
        for candidate in default_candidates
        if (normalized := _normalize_phone(candidate))
    }
    return normalized


ADMIN_PHONE_CANDIDATES = _admin_phone_candidates()


def _to_job_read(job: JobPost, owner: Optional[User] = None) -> JobRead:
    data = JobRead.model_validate(job, from_attributes=True)
    if owner:
        if owner.role == UserRole.ADMIN:
            data.owner_name = "관리자"
            data.owner_is_admin = True
        else:
            nickname = owner.nickname or ""
            if nickname:
                display = nickname
            elif owner.phone_number:
                display = f"회원{owner.phone_number[-4:]}"
            else:
                display = str(owner.user_id)
            data.owner_name = display
            data.owner_is_admin = False
    return data


def _public_media_url(path: str) -> str:
    name = pathlib.Path(path).name
    return f"/media/{name}"


def _unique(values: list[Optional[str]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)]


def _coerce_uuid_list(value: Any) -> list[UUID]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    items: list[UUID] = []
    for item in values:
        try:
            items.append(UUID(str(item)))
        except (TypeError, ValueError):
            continue
    return items


def _find_admin_user(db: Session) -> Optional[User]:
    admin_numbers = {
        normalized
        for phone in ADMIN_PHONE_CANDIDATES
        if (normalized := _normalize_phone(phone))
    }
    if not admin_numbers:
        return None
    stmt = select(User).where(User.phone_number.in_(admin_numbers))
    return db.exec(stmt).scalars().first()


def _resolve_seed_owner_id(db: Session, fallback_user_id: UUID) -> UUID:
    admin_user = _find_admin_user(db)
    if admin_user:
        return admin_user.user_id
    env_admin_id = os.getenv("ADMIN_USER_ID")
    if env_admin_id:
        try:
            return UUID(env_admin_id)
        except ValueError:
            logger.warning("Invalid ADMIN_USER_ID '%s' ignored", env_admin_id)
    return fallback_user_id


def _fetch_owner_map(db: Session, jobs: List[JobPost]) -> Dict[UUID, User]:
    owner_ids = {job.owner_id for job in jobs if getattr(job, "owner_id", None)}
    if not owner_ids:
        return {}
    stmt = select(User).where(User.user_id.in_(owner_ids))
    owners = db.exec(stmt).scalars().all()
    return {owner.user_id: owner for owner in owners}


def _fetch_match_info(db: Session, applicant_ids: List[UUID]) -> Dict[UUID, ApplicantMatchInfo]:
    if not applicant_ids:
        return {}
    unique_ids = list({aid for aid in applicant_ids if aid})
    if not unique_ids:
        return {}

    info: Dict[UUID, ApplicantMatchInfo] = {
        applicant_id: ApplicantMatchInfo() for applicant_id in unique_ids
    }

    app_counts_stmt = (
        select(
            JobApplication.applicant_id,
            func.count().label("total_apps"),
            func.max(JobApplication.applied_at).label("last_app_at"),
        )
        .where(JobApplication.applicant_id.in_(unique_ids))
        .group_by(JobApplication.applicant_id)
    )
    for applicant_id, total_apps, last_app_at in db.exec(app_counts_stmt):
        entry = info.setdefault(applicant_id, ApplicantMatchInfo())
        entry.total_applications = int(total_apps or 0)
        entry.last_applied_at = last_app_at

    match_counts_stmt = (
        select(
            JobApplication.applicant_id,
            func.count().label("total_matches"),
            func.max(JobApplication.applied_at).label("last_match_at"),
        )
        .where(
            JobApplication.status == ApplicationStatus.APPROVED,
            JobApplication.applicant_id.in_(unique_ids),
        )
        .group_by(JobApplication.applicant_id)
    )
    for applicant_id, total_matches, last_match_at in db.exec(match_counts_stmt):
        entry = info.setdefault(applicant_id, ApplicantMatchInfo())
        entry.total_matches = int(total_matches or 0)
        entry.last_matched_at = last_match_at

    for applicant_id in unique_ids:
        recent_any = (
            db.exec(
                select(JobApplication, JobPost)
                .join(JobPost, JobApplication.job_id == JobPost.id)
                .where(JobApplication.applicant_id == applicant_id)
                .order_by(JobApplication.applied_at.desc())
                .limit(1)
            ).first()
        )
        if recent_any:
            _, job = recent_any
            info.setdefault(applicant_id, ApplicantMatchInfo()).last_applied_job = (
                job.title
            )

        recent_match = (
            db.exec(
                select(JobApplication, JobPost)
                .join(JobPost, JobApplication.job_id == JobPost.id)
                .where(
                    JobApplication.applicant_id == applicant_id,
                    JobApplication.status == ApplicationStatus.APPROVED,
                )
                .order_by(JobApplication.applied_at.desc())
                .limit(1)
            ).first()
        )
        if recent_match:
            _, job = recent_match
            info.setdefault(applicant_id, ApplicantMatchInfo()).last_matched_job = job.title

    return info


def _collect_media_from_uploads(upload_ids: list[UUID], db: Session) -> tuple[list[str], list[str]]:
    raw_files: list[str] = []
    images: list[str] = []
    if not upload_ids:
        return raw_files, images

    for upload_id in upload_ids:
        upload = db.get(MediaUpload, upload_id)
        if not upload:
            continue
        extra = upload.extra or {}
        raw_url = extra.get("raw_url") or _public_media_url(upload.file_path)
        converted = extra.get("converted_urls") or []
        if raw_url:
            raw_files.append(str(raw_url))
        if converted:
            images.extend([str(url) for url in converted if url])
        elif raw_url:
            images.append(str(raw_url))

    return raw_files, images


@router.get("", response_model=JobListResponse)
def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    near_lat: Optional[float] = Query(
        None, description="현재 위치 위도 (근처 정렬용)"
    ),
    near_lng: Optional[float] = Query(
        None, description="현재 위치 경도 (근처 정렬용)"
    ),
    near_limit: Optional[int] = Query(
        100, ge=1, le=500, description="근처 정렬 시 최대 반환 개수"
    ),
    db: Session = Depends(get_db),
):
    stmt = select(JobPost).order_by(JobPost.created_at.desc())
    if status_filter:
        stmt = stmt.where(JobPost.status == status_filter)
    else:
        stmt = stmt.where(JobPost.status != JobStatus.DRAFT)

    is_near_query = near_lat is not None and near_lng is not None
    effective_per_page = per_page
    if is_near_query:
        lat_factor = 111320.0
        lng_factor = lat_factor * math.cos(math.radians(float(near_lat)))
        distance_expr = func.sqrt(
            func.pow((JobPost.lat - near_lat) * lat_factor, 2)
            + func.pow((JobPost.lng - near_lng) * lng_factor, 2)
        )
        stmt = (
            stmt.where(JobPost.lat.isnot(None), JobPost.lng.isnot(None))
            .order_by(distance_expr.asc(), JobPost.created_at.desc())
        )
        limit_value = near_limit or effective_per_page
        effective_per_page = min(limit_value, effective_per_page)

    total = db.exec(select(func.count()).select_from(stmt.subquery())).scalar_one()
    jobs = db.exec(_paginate(stmt, page, effective_per_page)).scalars().all()

    owner_map = _fetch_owner_map(db, jobs)
    items = [_to_job_read(job, owner_map.get(job.owner_id)) for job in jobs]
    has_more = page * effective_per_page < total

    return JobListResponse(
        items=items,
        page=page,
        per_page=effective_per_page,
        total=total,
        has_more=has_more,
    )


@router.get("/recommend", response_model=List[Dict[str, Any]])
def list_recommended_jobs(
    limit: int = Query(3, ge=1, le=10),
    intent: Optional[str] = Query(default=None, description="AI 추천 시 사용할 추가 의도/키워드"),
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """AI Orchestrator 기반 추천"""

    user = db.get(User, current_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    profile = _build_user_profile(user)
    pipeline = get_pipeline()
    result = pipeline.recommend(
        user_profile=profile.dict(),
        intent=intent or "",
        previous_recommendations=[],
    )
    recs = result.get("recommendations") or []
    formatted: List[Dict[str, Any]] = []
    for rec in recs[:limit]:
        reason = (
            rec.get("recommendation_reason")
            or rec.get("reason")
            or "AI가 프로필과 잘 맞다고 판단했어요."
        )
        formatted.append(
            {
                "job_id": rec.get("job_id"),
                "title": rec.get("title") or rec.get("job_title"),
                "description": rec.get("description"),
                "place": rec.get("place"),
                "address": rec.get("address"),
                "location": rec.get("location"),
                "lat": rec.get("lat") or rec.get("latitude"),
                "lng": rec.get("lng") or rec.get("longitude"),
                "work_days": rec.get("work_days"),
                "start_time": rec.get("start_time"),
                "end_time": rec.get("end_time"),
                "hourly_wage": rec.get("hourly_wage"),
                "pay_text": rec.get("pay_text") or rec.get("wage"),
                "client": rec.get("client"),
                "source": rec.get("source") or "ai",
                "recommendation_reason": reason,
            }
        )
    if not formatted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="추천 결과가 없습니다.")
    return formatted


@router.post("/seed-from-csv", response_model=JobSeedResponse)
def seed_jobs_from_csv_endpoint(
    payload: Optional[JobSeedRequest] = None,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    payload = payload or JobSeedRequest()
    csv_path = pathlib.Path(payload.csv_path or DEFAULT_SEED_CSV)
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"CSV 파일을 찾을 수 없습니다: {csv_path}")

    seed_owner_id = _resolve_seed_owner_id(db, current_user_id)
    admin_user = _find_admin_user(db)
    if admin_user and admin_user.user_id == seed_owner_id:
        reassigned = db.exec(
            select(JobPost).where(
                JobPost.source == "ai_seed",
                JobPost.owner_id != seed_owner_id,
            )
        ).all()
        if reassigned:
            for job in reassigned:
                job.owner_id = seed_owner_id
            db.commit()

    geocoders = []
    if os.getenv("NAVER_MAPS_CLIENT_ID") and os.getenv("NAVER_MAPS_CLIENT_SECRET"):
        try:
            geocoders.append(NaverGeocoder(cache_path=_NAVER_GEOCODER_CACHE))
        except Exception as exc:  # pragma: no cover - optional feature
            logger.warning("Naver geocoder unavailable for seeding: %s", exc)
    google_key = os.getenv("GOOGLE_GEOCODING_API_KEY") or os.getenv("GOOGLE_GEOCODING")
    if google_key:
        try:
            geocoders.append(GoogleGeocoder(cache_path=_GOOGLE_GEOCODER_CACHE))
        except Exception as exc:  # pragma: no cover
            logger.warning("Google geocoder unavailable for seeding: %s", exc)

    inserted = seed_jobs_from_csv(
        db,
        owner_id=seed_owner_id,
        csv_path=csv_path,
        limit=payload.limit,
        clear_existing=payload.clear,
        geocoders=geocoders,
    )
    total = db.exec(select(func.count()).select_from(select(JobPost.id).subquery())).scalar_one()
    return JobSeedResponse(success=True, inserted=inserted, total=total)


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    owner = db.get(User, current_user_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    lat, lng = _guess_coordinates(payload.address, payload.place)
    lat_override = _coerce_float(payload.lat)
    lng_override = _coerce_float(payload.lng)
    if lat_override is not None:
        lat = lat_override
    if lng_override is not None:
        lng = lng_override

    job = JobPost(
        owner_id=current_user_id,
        title=payload.title,
        description=payload.description,
        participants=payload.participants,
        hourly_wage=payload.hourly_wage,
        place=payload.place,
        address=payload.address,
        location=payload.place,
        work_days=payload.work_days,
        start_time=payload.start_time,
        end_time=payload.end_time,
        schedule=", ".join(payload.work_days) if payload.work_days else None,
        time=f"{payload.start_time}~{payload.end_time}",
        pay_text=f"시급 {payload.hourly_wage:,}원",
        wage=str(payload.hourly_wage),
        client=payload.client,
        lat=lat,
        lng=lng,
        source="manual",
        images=_unique(_coerce_str_list(payload.images)),
        raw_media=_unique(_coerce_str_list(payload.raw_media)),
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return _to_job_read(job, owner)


@router.post("/from-image", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_from_ai(
    payload: JobAiCreate,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    fields = payload.fields or {}

    title = str(fields.get("title") or "AI 생성 공고")
    description = str(fields.get("description") or "AI가 생성한 공고 내용을 확인해주세요.")
    location_text = fields.get("location") or fields.get("place")
    lat, lng = _guess_coordinates(fields.get("address"), location_text)
    lat_override = _coerce_float(fields.get("lat") or fields.get("latitude"))
    lng_override = _coerce_float(fields.get("lng") or fields.get("longitude"))
    if lat_override is not None:
        lat = lat_override
    if lng_override is not None:
        lng = lng_override

    hourly = None
    wage_field = fields.get("wage") or fields.get("pay")
    if isinstance(wage_field, (int, float)):
        hourly = int(wage_field)
    elif isinstance(wage_field, str):
        digits = "".join(ch for ch in wage_field if ch.isdigit())
        if digits:
            hourly = int(digits)

    provided_images = _coerce_str_list(fields.get("images") or fields.get("image_urls"))
    provided_raw_media = _coerce_str_list(fields.get("raw_media") or fields.get("source_files"))
    upload_ids = list(payload.upload_ids or [])
    upload_ids.extend(_coerce_uuid_list(fields.get("upload_ids")))
    raw_from_uploads, images_from_uploads = _collect_media_from_uploads(upload_ids, db)
    job_images = _unique(provided_images + images_from_uploads)
    job_raw_media = _unique(provided_raw_media + raw_from_uploads)

    job = JobPost(
        owner_id=current_user_id,
        title=title,
        description=description,
        requirements=fields.get("requirements"),
        category=fields.get("category"),
        place=location_text,
        address=fields.get("address") or location_text,
        location=location_text,
        schedule=fields.get("schedule"),
        time=fields.get("time"),
        duration=fields.get("duration"),
        wage=wage_field if isinstance(wage_field, str) else None,
        hourly_wage=hourly,
        pay_text=wage_field if isinstance(wage_field, str) else None,
        work_days=_coerce_str_list(fields.get("work_days")),
        lat=lat,
        lng=lng,
        ai_confidence=fields.get("confidence"),
        ai_summary={"raw_fields": fields},
        source="ai-image",
        images=job_images,
        raw_media=job_raw_media,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    owner = db.get(User, current_user_id)

    return {
        "job_id": str(job.id),
        "job": _to_job_read(job, owner).model_dump(mode="json"),
        "status": "created",
    }


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(JobPost, _coerce_uuid(job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공고를 찾을 수 없습니다.")

    job.views += 1
    db.add(job)
    db.commit()
    db.refresh(job)

    owner = db.get(User, job.owner_id)
    return _to_job_read(job, owner)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: str,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    job = db.get(JobPost, _coerce_uuid(job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공고를 찾을 수 없습니다.")
    if job.owner_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="삭제 권한이 없습니다.")

    db.delete(job)
    db.commit()


@router.patch("/{job_id}", response_model=JobRead)
def update_job_status(
    job_id: str,
    payload: JobStatusUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    job = db.get(JobPost, _coerce_uuid(job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공고를 찾을 수 없습니다.")
    if job.owner_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="수정 권한이 없습니다.")

    job.status = payload.status
    db.add(job)
    db.commit()
    db.refresh(job)

    owner = db.get(User, job.owner_id)
    return _to_job_read(job, owner)


@router.get("/{job_id}/applicants", response_model=JobApplicantListResponse)
def list_applicants(
    job_id: str,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    job = db.get(JobPost, _coerce_uuid(job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공고를 찾을 수 없습니다.")
    if job.owner_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="열람 권한이 없습니다.")

    stmt = (
        select(JobApplication, User)
        .join(User, JobApplication.applicant_id == User.user_id)
        .where(
            JobApplication.job_id == job.id,
            JobApplication.status != ApplicationStatus.CANCELLED,
        )
        .order_by(JobApplication.applied_at.desc())
    )
    rows = db.exec(stmt).all()
    applicant_ids = [application.applicant_id for application, _ in rows]
    match_map = _fetch_match_info(db, applicant_ids)

    items: list[JobApplicantRead] = []
    for application, applicant in rows:
        items.append(
            JobApplicantRead(
                id=application.id,
                job_id=application.job_id,
                applicant_id=application.applicant_id,
                status=application.status,
                note=application.note,
                applied_at=application.applied_at,
                name=applicant.nickname or applicant.phone_number[-4:],
                nickname=applicant.nickname,
                region=applicant.location,
                experience=(applicant.preferences or {}).get("experience")
                if isinstance(applicant.preferences, dict)
                else None,
                match_info=match_map.get(application.applicant_id),
            )
        )

    return JobApplicantListResponse(items=items, total=len(items))

@router.get("/my/jobs", response_model=JobListResponse)
def list_my_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    stmt = (
        select(JobPost)
        .where(
            JobPost.owner_id == current_user_id,
            or_(JobPost.source.is_(None), JobPost.source != "ai_seed"),
        )
        .order_by(JobPost.created_at.desc())
    )

    total = db.exec(select(func.count()).select_from(stmt.subquery())).scalar_one()
    jobs = db.exec(_paginate(stmt, page, per_page)).scalars().all()

    owner_map = _fetch_owner_map(db, jobs)
    items = [_to_job_read(job, owner_map.get(job.owner_id)) for job in jobs]
    has_more = page * per_page < total

    return JobListResponse(items=items, page=page, per_page=per_page, total=total, has_more=has_more)
import pathlib
