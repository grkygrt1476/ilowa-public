"""Pydantic schemas for notification APIs."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool = False
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class NotificationListResponse(BaseModel):
    items: List[NotificationRead]


class NotificationMarkRequest(BaseModel):
    is_read: bool = True
