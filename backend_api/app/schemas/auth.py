"""
auth.py
이 모듈은 회원가입 및 로그인 플로우를 위한 모든 Pydantic/SQLModel 스키마를 정의합니다.
이는 프론트엔드와 백엔드 간의 데이터 계약 역할을 수행합니다.
"""
from typing import Optional, Dict, Literal, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, validator, Field as PydanticField

# # Profile파일 섞여서 추가본
# class ProfileSummaryResponse(BaseModel):
#     user_id: UUID
#     nickname: Optional[str] = None
#     region: Optional[str] = None       # users.py에서 User.location을 매핑
#     badges: List[str] = PydanticField(default_factory=list)
    
# ----------------------------------------------------
# 1. Request Models (프론트엔드 -> 백엔드)
# ----------------------------------------------------

class PhoneRequest(BaseModel):
    """전화번호 등록 시작 및 OTP 발송 요청 본문"""
    phone_number: str = PydanticField(..., description="휴대폰 번호 (하이픈 제외 11자리)", pattern=r"^010\d{8}$")

class OTPRequest(PhoneRequest):
    """OTP 발송 요청 본문"""
    purpose: Literal["register", "login"] = PydanticField(..., description="요청 목적: 'register' 또는 'login'")


class OTPVerifyRequest(BaseModel):
    """OTP 코드 인증 요청 본문"""
    phone_number: str = PydanticField(
        ..., pattern=r"^010\d{8}$",
        description="휴대폰 번호 (하이픈 제외 11자리)"
    )
    code: str = PydanticField(
        ..., alias="otp_code", pattern=r"^\d{6}$",
        description="SMS로 수신한 6자리 인증 코드 (필드명 code 또는 otp_code 모두 허용)"
    )
    purpose: Literal["register", "login"] = PydanticField(
        ..., description="요청 목적: 'register' 또는 'login'"
    )

    model_config = {
        "populate_by_name": True,   # code 또는 otp_code 둘 다 허용
        "extra": "ignore",          # 불필요 필드 무시(422 예방)
    }


class PINSetRequest(BaseModel):
    """PIN 설정 및 확인 요청 본문"""
    phone_number: str = PydanticField(..., description="휴대폰 번호 (하이픈 제외 11자리)", pattern=r"^010\d{8}$")
    pin: str = PydanticField(..., description="4자리 PIN", pattern=r"^\d{4}$")
    confirm_pin: str = PydanticField(..., description="PIN 확인 (1차와 일치해야 함)", pattern=r"^\d{4}$")
    setup_token: str = PydanticField(..., description="OTP 검증 성공 시 발급받은 임시 JWT 토큰")
    
    @validator('confirm_pin')
    def pins_match(cls, v, values, **kwargs):
        if 'pin' in values and v != values['pin']:
            raise ValueError('PIN이 일치하지 않습니다.')
        return v

class PINLoginRequest(BaseModel):
    """PIN 로그인 요청 본문"""
    phone_number: str = PydanticField(..., description="휴대폰 번호 (하이픈 제외 11자리)", pattern=r"^010\d{8}$")
    pin: str = PydanticField(..., description="4자리 PIN", pattern=r"^\d{4}$")

class UserProfileUpdateRequest(BaseModel):
    """PATCH /api/v1/users/me 요청 본문 (모든 업데이트 가능한 필드)"""
    nickname: Optional[str] = PydanticField(None, min_length=2, max_length=20, description="닉네임 (~20자)")
    location: Optional[str] = PydanticField(None, description="사용자 선호 지역명 (예: 성동구, 강남구)")
    preferences: Optional[Dict] = PydanticField(None, description="사용자 선호/비선호 항목 JSON")
    request_role: Optional[str] = PydanticField(None, description="EMPLOYER 역할로 변경 요청")

class PinRegisterRequest(BaseModel):
    phone_number: str = PydanticField(..., pattern=r"^010\d{8}$", description="하이픈 제외 11자리")
    pin: str = PydanticField(..., pattern=r"^\d{4}$", description="4자리 PIN")
    model_config = {"extra": "ignore"}
    
# ----------------------------------------------------
# 2. Response Models (백엔드 -> 프론트엔드)
# ----------------------------------------------------

class OTPRequestSuccess(BaseModel):
    """OTP 발송 성공 응답"""
    phone_number: str
    expires_in: int = PydanticField(description="OTP 코드 만료 시간 (초)")
    cooldown: int = PydanticField(description="재전송까지 남은 시간 (초)")
    message: str = "인증번호가 발송되었습니다."

class VerifiedResponse(BaseModel):
    """OTP 검증 성공 응답"""
    verified: bool = True
    setup_token: Optional[str] = PydanticField(None, description="PIN 설정을 위한 임시 JWT 토큰") 
    message: str = "인증에 성공했습니다."

class TokenResponse(BaseModel):
    """로그인 및 최종 가입 성공 응답 (JWT 토큰 포함)"""
    user_id: UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = PydanticField(description="Access Token 만료 시간 (초)")
    message: str = "로그인/가입이 완료되었습니다."

class MessageResponse(BaseModel):
    """간단한 성공 또는 오류 메시지 응답"""
    message: str

class AgreementsRequest(BaseModel):
    terms: bool = PydanticField(False, description="이용약관 동의")
    privacy: bool = PydanticField(False, description="개인정보 처리방침 동의")
    marketing: bool | None = PydanticField(False, description="마케팅 수신 동의(선택)")
    model_config = {"extra": "ignore"}
