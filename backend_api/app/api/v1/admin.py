"""Admin specific authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from backend_api.app.db.database import get_db
from backend_api.app.db.models import UserRole
from backend_api.app.schemas.auth import PINLoginRequest, TokenResponse
from backend_api.app.services.auth_service import AuthService


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/login/pin", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login_admin_with_pin(req: PINLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    user = service._get_user_by_phone(req.phone_number)  # noqa: SLF001 - internal helper
    if not user or user.role not in {UserRole.ADMIN, UserRole.EMPLOYER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 없습니다.")

    token_info = service.login_with_pin(req)
    return token_info

