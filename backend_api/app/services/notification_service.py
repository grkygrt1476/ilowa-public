"""Helper functions for creating notifications."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlmodel import Session

from backend_api.app.db.models import Notification


def add_notification(
    db: Session,
    *,
    user_id: UUID,
    title: str,
    message: str,
    link: Optional[str] = None,
    ntype: str = "general",
) -> Notification:
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
        type=ntype,
    )
    db.add(notif)
    return notif
