from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    nickname: str
    regions: List[str] = Field(default_factory=list)
    days: List[str] = Field(default_factory=list)
    time_slots: List[str] = Field(default_factory=list)
    experiences: List[str] = Field(default_factory=list)
    capabilities: Dict[str, Any] = Field(default_factory=dict)


class RecommendationRequest(BaseModel):
    user_profile: UserProfile
    intent: Optional[str] = Field(default="")

