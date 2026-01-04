import uuid
from typing import Optional, Dict, Any # Dict, Any 임포트 추가
from datetime import datetime, timezone
from enum import Enum 

from sqlmodel import Field, SQLModel, Column, JSON # Column, JSON 임포트 추가

# ====================================================
# 0. 역할(Role) Enum 정의: 구직자/구인자 트랙 분리
# ====================================================

class UserRole(str, Enum):
    """사용자 역할을 정의하는 Enum (데이터 무결성 확보)"""
    JOB_SEEKER = "JOB_SEEKER"  # 구직자 (시니어 사용자)
    EMPLOYER = "EMPLOYER"      # 구인자 (고용주/기관)
    ADMIN = "ADMIN"            # 관리자

# ----------------------------------------------------
# 1. Users 테이블 모델
# ----------------------------------------------------

class UserBase(SQLModel):
    """"DB 테이블 컬럼의 기본 정의 (Base Schema)"""
    phone_number: str = Field(index=True, unique=True, nullable=False)
    nickname: Optional[str] = Field(None, min_length=2, max_length=20) 
    location: Optional[str] = Field(None, min_length=2, max_length=20)
    role: UserRole = Field(default=UserRole.JOB_SEEKER, nullable=False) 

class User(UserBase, table=True):
    """실제 DB Users 테이블 모델 (User + Profile 속성 통합)"""
    # UUID를 기본 키(Primary Key)로 설정하고 uuid4로 자동 생성
    user_id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)    

    # 보안 필드
    pin_hash: str = Field(nullable=False) # ✨ 수정: nullabe -> nullable 오타 수정
    is_verified: bool = Field(default=False)

    # ✨ 신규 통합 필드 (profiles.py에서 이동)
    preferences: Dict[str, Any] = Field(
        default={}, 
        sa_column=Column(JSON), 
        description="사용자 선호 항목 (JSONB)"
    )
    point_balance: int = Field(default=0, description="현재 포인트 잔액")
    is_onboarding_complete: bool = Field(default=False)
    last_login: Optional[datetime] = Field(
        default=None,
        description="마지막 로그인 시각",
        nullable=True,
    )

    # 타임스탬프
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        nullable=False
    )

# ----------------------------------------------------
# 2. OTP 인증 상태 관리 테이블 모델
# ----------------------------------------------------

class OTPVerificationRequest(SQLModel, table =True):
    """"OTP 인증 시도 및 상태 관리를 위한 임시 테이블"""
    otp_id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    phone_number: str = Field(index=True, nullable=False)

    # OTP 코드
    otp_code: str = Field(nullable=False)
    expires_at: datetime = Field(nullable=False)
    purpose: str = Field(nullable=False)

    # 보안 및 흐름 제어 필드
    attempts_count: int = Field(default=0)
    is_used: bool = Field(default=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
