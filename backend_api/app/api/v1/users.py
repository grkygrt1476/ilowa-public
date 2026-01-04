# backend_api/app/api/v1/users.py

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import Session

from backend_api.app.db.database import get_db
from backend_api.app.db.models.auth import User  # 통합된 User 모델
from backend_api.app.schemas.auth import UserProfileUpdateRequest
from backend_api.app.schemas import profile as profile_schemas
from backend_api.app.core.security import get_current_user_id  # JWT 인증 의존성

router = APIRouter(
    prefix="/users",
    tags=["User - 사용자/프로필"],
)

# 의존성 타입
CurrentUserIdDep = Annotated[uuid.UUID, Depends(get_current_user_id)]
DbSessionDep = Annotated[Session, Depends(get_db)]


@router.get(
    "/me",
    response_model=profile_schemas.ProfileSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="현재 사용자 프로필 요약 조회",
)
async def get_my_profile(
    current_user_id: CurrentUserIdDep,
    db: DbSessionDep,
):
    """
    Authorization: Bearer <access_token> 필요.
    통합된 User 모델에서 닉네임/지역/온보딩 상태를 반환합니다.
    """
    # PK가 user_id인 모델이라고 가정합니다.
    user = db.get(User, current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다."
        )
    
    account = profile_schemas.ProfileAccountSummary(
        nickname=user.nickname,
        region=user.location,
        phone=user.phone_number,
    )

    return profile_schemas.ProfileSummaryResponse(
        user_id=user.user_id,                        # user.id -> user.user_id
        nickname=user.nickname,
        region=user.location,                        # 응답 필드명은 region, 저장 필드는 location
        account=account,
        badges=["온보딩 완료"] if user.is_onboarding_complete else ["최소 프로필 필요"],
    )


@router.patch(
    "/me",
    response_model=profile_schemas.ProfileSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="현재 사용자 프로필 업데이트",
)
async def update_my_profile(
    req: UserProfileUpdateRequest,
    current_user_id: CurrentUserIdDep,
    db: DbSessionDep,
):
    """
    현재 인증된 사용자의 닉네임/지역 등을 업데이트합니다.
    """
    user = db.get(User, current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다."
        )

    # 변경 요청된 필드만 반영
    update_data = req.model_dump(exclude_unset=True)

    if "nickname" in update_data:
        user.nickname = update_data["nickname"]
    if "location" in update_data:
        user.location = update_data["location"]

    db.add(user)
    db.commit()
    db.refresh(user)

    account = profile_schemas.ProfileAccountSummary(
        nickname=user.nickname,
        region=user.location,
        phone=user.phone_number,
    )

    return profile_schemas.ProfileSummaryResponse(
        user_id=user.user_id,
        nickname=user.nickname,
        region=user.location,
        account=account,
        badges=["업데이트 완료"],
    )
