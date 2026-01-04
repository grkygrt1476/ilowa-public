"""Profile onboarding endpoints consumed by the new UI."""
from __future__ import annotations

import uuid
from typing import Annotated, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from backend_api.app.core.security import get_current_user_id
from backend_api.app.db.database import get_db
from backend_api.app.db.models.auth import User
from backend_api.app.schemas import profile as profile_schemas

router = APIRouter(tags=["Profile - 온보딩"])

CurrentUserIdDep = Annotated[uuid.UUID, Depends(get_current_user_id)]
DbSessionDep = Annotated[Session, Depends(get_db)]


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    return user


def _merge_preferences(user: User, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Utility to merge preference payload into persisted JSON safely."""

    current = dict(user.preferences or {})
    current.update(updates)
    user.preferences = current
    return current


@router.put("/api/v1/profile/account", response_model=profile_schemas.ProfileSummaryResponse)
@router.put("/profile/account", response_model=profile_schemas.ProfileSummaryResponse, include_in_schema=False)
async def update_account_profile(
    req: profile_schemas.ProfileAccountUpdateRequest,
    current_user_id: CurrentUserIdDep,
    db: DbSessionDep,
):
    """Update nickname/location basics coming from the onboarding nickname screen."""

    user = _get_user_or_404(db, current_user_id)

    data = req.model_dump(exclude_unset=True)
    if "nickname" in data:
        user.nickname = data["nickname"]
    if "location" in data:
        user.location = data["location"]

    db.add(user)
    db.commit()
    db.refresh(user)

    return await get_profile_summary(current_user_id, db)  # type: ignore[misc]


@router.put("/api/v1/profile/prefs/location", response_model=profile_schemas.ProfileSummaryResponse)
@router.put("/profile/prefs/location", response_model=profile_schemas.ProfileSummaryResponse, include_in_schema=False)
async def save_location_preferences(
    req: profile_schemas.LocationPreferenceRequest,
    current_user_id: CurrentUserIdDep,
    db: DbSessionDep,
):
    """Persist preferred working location and update the primary location string."""

    user = _get_user_or_404(db, current_user_id)

    prefs = _merge_preferences(
        user,
        {
            "location": {
                "use_gps": req.use_gps,
                "regions": req.regions,
            },
            "region": (req.regions[0] if not req.use_gps and req.regions else user.location),
        },
    )

    if not req.use_gps and req.regions:
        user.location = req.regions[0]

    db.add(user)
    db.commit()
    db.refresh(user)

    return await get_profile_summary(current_user_id, db)  # type: ignore[misc]


@router.put("/api/v1/profile/prefs/time", response_model=profile_schemas.ProfileSummaryResponse)
@router.put("/profile/prefs/time", response_model=profile_schemas.ProfileSummaryResponse, include_in_schema=False)
async def save_time_preferences(
    req: profile_schemas.TimePreferenceRequest,
    current_user_id: CurrentUserIdDep,
    db: DbSessionDep,
):
    """Save preferred days and time slots."""

    user = _get_user_or_404(db, current_user_id)

    _merge_preferences(
        user,
        {
            "days": req.days,
            "time_slots": req.time_slots,
        },
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return await get_profile_summary(current_user_id, db)  # type: ignore[misc]


@router.put("/api/v1/profile/prefs/history", response_model=profile_schemas.ProfileSummaryResponse)
@router.put("/profile/prefs/history", response_model=profile_schemas.ProfileSummaryResponse, include_in_schema=False)
async def save_history_preferences(
    req: profile_schemas.HistoryPreferenceRequest,
    current_user_id: CurrentUserIdDep,
    db: DbSessionDep,
):
    """Persist past job experiences information."""

    user = _get_user_or_404(db, current_user_id)

    experiences = req.experiences or []
    _merge_preferences(
        user,
        {
            "experiences": experiences,
            "experience_none": bool(req.none),
        },
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return await get_profile_summary(current_user_id, db)  # type: ignore[misc]


@router.put("/api/v1/profile/prefs/capability", response_model=profile_schemas.ProfileSummaryResponse)
@router.put("/profile/prefs/capability", response_model=profile_schemas.ProfileSummaryResponse, include_in_schema=False)
async def save_capability_preferences(
    req: profile_schemas.CapabilityPreferenceRequest,
    current_user_id: CurrentUserIdDep,
    db: DbSessionDep,
):
    """Save preferred physical workload intensity."""

    user = _get_user_or_404(db, current_user_id)

    capability_payload = {
        "physical_level": req.physical_level,
        "can_stand_long": req.physical_level in {"high", "medium"},
    }

    _merge_preferences(
        user,
        {
            "physical_level": req.physical_level,
            "capabilities": capability_payload,
        },
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return await get_profile_summary(current_user_id, db)  # type: ignore[misc]


@router.get("/api/v1/profile/summary", response_model=profile_schemas.ProfileSummaryResponse)
@router.get("/profile/summary", response_model=profile_schemas.ProfileSummaryResponse, include_in_schema=False)
async def get_profile_summary(
    current_user_id: CurrentUserIdDep,
    db: DbSessionDep,
):
    """Return the merged summary data consumed by the onboarding summary screen."""

    user = _get_user_or_404(db, current_user_id)

    phone_number = user.phone_number
    location = user.location
    nickname = user.nickname
    avatar_url = getattr(user, "avatar_url", None)

    prefs = dict(user.preferences or {})
    location_pref = prefs.get("location", {}) or {}
    regions = location_pref.get("regions") or []
    region = prefs.get("region") or user.location or (regions[0] if regions else None)

    experiences = prefs.get("experiences") or []
    physical_level = prefs.get("physical_level")
    capabilities = prefs.get("capabilities") or {}

    snapshot = profile_schemas.ProfilePreferencesSnapshot(
        location={
            "use_gps": bool(location_pref.get("use_gps")),
            "regions": regions,
        },
        region=region,
        days=prefs.get("days") or [],
        time_slots=prefs.get("time_slots") or [],
        experiences=experiences,
        physical_level=physical_level,
    )

    account = profile_schemas.ProfileAccountSummary(
        nickname=user.nickname,
        phone=user.phone_number,
        region=region,
    )

    return profile_schemas.ProfileSummaryResponse(
        user_id=user.user_id,
        nickname=nickname,
        region=region,
        account=account,
        prefs=snapshot,
        experiences=experiences,
        physical_level=physical_level,
        capabilities=capabilities or (
            {"physical_level": physical_level, "can_stand_long": bool(physical_level in {"high", "medium"})}
            if physical_level
            else {}
        ),
        badges=["온보딩 완료"] if user.is_onboarding_complete else ["온보딩 진행중"],
        # account=profile_schemas.ProfileAccountSummary(
        #     phone=phone_number,
        #     region=location,
        #     nickname=nickname,
        #     avatar_url=avatar_url,
        # ),
    )


@router.post("/api/v1/profile/save", response_model=profile_schemas.ProfileSaveResponse)
@router.post("/profile/save", response_model=profile_schemas.ProfileSaveResponse, include_in_schema=False)
async def finalize_profile(
    current_user_id: CurrentUserIdDep,
    db: DbSessionDep,
):
    """Mark onboarding flow as completed."""

    user = _get_user_or_404(db, current_user_id)
    user.is_onboarding_complete = True

    db.add(user)
    db.commit()
    db.refresh(user)

    return profile_schemas.ProfileSaveResponse(
        user_id=user.user_id,
        is_onboarding_complete=user.is_onboarding_complete,
    )
