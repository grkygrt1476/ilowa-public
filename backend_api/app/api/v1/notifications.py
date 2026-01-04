"""Notification endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend_api.app.core.security import get_current_user_id
from backend_api.app.db.database import get_db
from backend_api.app.db.models import Notification
from backend_api.app.schemas.notifications import (
    NotificationListResponse,
    NotificationMarkRequest,
    NotificationRead,
)


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user_id)
        .order_by(Notification.created_at.desc())
    )
    notifications = db.exec(stmt).all()
    items = [NotificationRead.model_validate(n, from_attributes=True) for n in notifications]
    return NotificationListResponse(items=items)


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_notification(
    notification_id: UUID,
    payload: NotificationMarkRequest | None = None,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    payload = payload or NotificationMarkRequest()
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    notification.is_read = payload.is_read
    if notification.is_read:
        notification.read_at = datetime.now(timezone.utc)
    else:
        notification.read_at = None
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return NotificationRead.model_validate(notification, from_attributes=True)
