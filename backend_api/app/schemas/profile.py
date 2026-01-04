"""Profile and onboarding related schemas."""
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ProfileAccountUpdateRequest(BaseModel):
    """Request body for updating basic account level profile data."""

    nickname: Optional[str] = Field(None, min_length=2, max_length=20)
    location: Optional[str] = Field(None, min_length=2, max_length=20)


class LocationPreferenceRequest(BaseModel):
    """Preferred working location payload."""

    use_gps: bool = False
    regions: List[str] = Field(default_factory=list, max_items=5)

    @model_validator(mode="after")
    def validate_regions(cls, values: "LocationPreferenceRequest") -> "LocationPreferenceRequest":  # type: ignore[name-defined]
        if not values.use_gps and not values.regions:
            raise ValueError("use_gps가 false인 경우 최소 한 개의 지역을 선택해야 합니다.")
        return values


class TimePreferenceRequest(BaseModel):
    """Preferred working days and time slots."""

    days: List[str] = Field(default_factory=list, max_items=7)
    time_slots: List[str] = Field(default_factory=list, max_items=6)

    @model_validator(mode="after")
    def validate_non_empty(cls, values: "TimePreferenceRequest") -> "TimePreferenceRequest":  # type: ignore[name-defined]
        if not values.days:
            raise ValueError("요일을 최소 한 개 이상 선택해주세요.")
        if not values.time_slots:
            raise ValueError("시간대를 최소 한 개 이상 선택해주세요.")
        return values


class HistoryPreferenceRequest(BaseModel):
    """Past job experiences selection."""

    experiences: Optional[List[str]] = Field(default=None)
    none: Optional[bool] = False

    @model_validator(mode="after")
    def validate_payload(cls, values: "HistoryPreferenceRequest") -> "HistoryPreferenceRequest":  # type: ignore[name-defined]
        if values.none:
            values.experiences = []
        elif not values.experiences:
            raise ValueError("경험이 있는 경우 최소 한 개 이상 선택해주세요.")
        return values


class CapabilityPreferenceRequest(BaseModel):
    """Physical capability level payload."""

    physical_level: str = Field(..., pattern=r"^(high|medium|low)$")


class ProfilePreferencesSnapshot(BaseModel):
    """Normalized snapshot returned to the frontend."""

    location: Dict[str, Any] = Field(default_factory=lambda: {"use_gps": False, "regions": []})
    region: Optional[str] = None
    days: List[str] = Field(default_factory=list)
    time_slots: List[str] = Field(default_factory=list)
    experiences: List[str] = Field(default_factory=list)
    physical_level: Optional[str] = None


class ProfileAccountSummary(BaseModel):
    """High level account information displayed in profile/My Page views."""

    nickname: Optional[str] = None
    phone: Optional[str] = None
    region: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileSummaryResponse(BaseModel):
    """Summary response consumed by onboarding UI."""

    user_id: UUID
    nickname: Optional[str] = None
    region: Optional[str] = None
    account: ProfileAccountSummary = Field(default_factory=ProfileAccountSummary)
    prefs: ProfilePreferencesSnapshot = Field(default_factory=ProfilePreferencesSnapshot)
    experiences: List[str] = Field(default_factory=list)
    physical_level: Optional[str] = None
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    badges: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def mirror_account_values(cls, model: "ProfileSummaryResponse") -> "ProfileSummaryResponse":
        """Ensure legacy top-level nickname/region fields stay in sync with account data."""

        account = model.account or ProfileAccountSummary()

        account_updates: Dict[str, Any] = {}

        if model.nickname and not account.nickname:
            account_updates["nickname"] = model.nickname
        if model.region and not account.region:
            account_updates["region"] = model.region

        if account_updates:
            account = account.model_copy(update=account_updates)

        if account.nickname and not model.nickname:
            model.nickname = account.nickname
        if account.region and not model.region:
            model.region = account.region

        model.account = account
        return model

class ProfileSaveResponse(BaseModel):
    """Response returned after marking onboarding as complete."""

    user_id: UUID
    is_onboarding_complete: bool
