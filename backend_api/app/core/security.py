import jwt
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError

from backend_api.app.core.config import settings
from backend_api.app.db.models.auth import User # 사용자 모델을 JWT 생성 시 사용하기 위해 임포트
from backend_api.app.core.hashers import Argon2Hasher, argon2_hasher

DIGITS = string.digits

# JWT 설정
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES # 기본 60분
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS # 기본 7일
SETUP_TOKEN_EXPIRE_MINUTES = 5 # PIN 설정을 위한 토큰은 5분만 유효

# JWT 인증 스키마 정의: HTTP 헤더에서 Bearer 토큰을 찾도록 FastAPI에 지시
# /api/v1/auth/login/pin 엔드포인트를 토큰 요청 URL로 지정
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login/pin", 
    scheme_name="JWT"
)

# dummy code
def generate_otp_code(length: int = 6) -> str:
    """
    OTP 코드 생성. 더미 모드(USE_DUMMY_SMS=true)면 settings.DUMMY_OTP_CODE 반환.
    """
    if getattr(settings, "USE_DUMMY_SMS", False):
        # .env 에서 DUMMY_OTP_CODE=0000 세팅해두면 여기로 고정
        return getattr(settings, "DUMMY_OTP_CODE", "000000")

    # 실제 난수 6자리 (필요 시 length를 4/6 등 바꿔 호출)
    return "".join(random.choice(DIGITS) for _ in range(length))
# ----------------------------------------------------
# 1. 토큰 생성 로직
# ----------------------------------------------------

def create_token(data: Dict[str, Any], expires_delta: timedelta) -> str:
    """주어진 데이터와 만료 기간으로 JWT 토큰을 생성합니다."""
    to_encode = data.copy()
    
    # 만료 시간 (exp) 및 발행 시간 (iat) 클레임 추가
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    to_encode.update({"exp": expire, "iat": now})
    
    # 설정된 SECRET_KEY와 ALGORITHM을 사용하여 인코딩
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_access_token(user_id: UUID) -> str:
    """Access Token 생성 (인증된 사용자용)"""
    delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_token(data={"sub": str(user_id), "type": "access"}, expires_delta=delta)

def create_refresh_token(user_id: UUID) -> str:
    """Refresh Token 생성 (세션 갱신용)"""
    delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return create_token(data={"sub": str(user_id), "type": "refresh"}, expires_delta=delta)

def create_setup_token(phone_number: str) -> str:
    """OTP 인증 후 PIN 설정을 위한 임시 Setup Token 생성"""
    delta = timedelta(minutes=SETUP_TOKEN_EXPIRE_MINUTES)
    # 'setup' 타입을 사용하여 PIN 설정 외의 다른 API 접근을 제한
    return create_token(data={"phone": phone_number, "type": "setup"}, expires_delta=delta)

# ----------------------------------------------------
# 2. 토큰 검증 및 디코딩 로직
# ----------------------------------------------------

def decode_token(token: str) -> Dict[str, Any]:
    """JWT 토큰을 디코딩하고 클레임을 반환합니다."""
    try:
        # settings.SECRET_KEY와 알고리즘을 사용하여 복호화
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # 토큰 만료 시 401 예외 발생
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다. 다시 로그인해 주세요.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        # 유효하지 않은 토큰 (서명 오류 등) 시 401 예외 발생
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ----------------------------------------------------
# 3. 인증 의존성 주입 (FastAPI Dependencies)
# ----------------------------------------------------

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> UUID:
    """
    HTTP 헤더에서 Access Token을 추출, 검증하여 user_id(UUID)를 반환합니다.
    """
    payload = decode_token(token)
    user_id_str = payload.get("sub")
    token_type = payload.get("type")

    # 토큰 타입이 'access'가 아니거나 sub 클레임이 없을 경우 인증 실패
    if user_id_str is None or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증에 실패했습니다. 유효한 Access Token이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 유효하지 않은 사용자 ID가 포함되어 있습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_setup_token(token: str, required_phone: str) -> bool:
    """
    Setup Token의 유효성을 검증하고, 클레임의 전화번호가 요청과 일치하는지 확인합니다.
    """
    payload = decode_token(token)
    token_type = payload.get("type")
    phone_in_token = payload.get("phone")

    # 토큰 타입이 'setup'이 아니거나, 토큰 속 전화번호가 요청 전화번호와 다르면 인증 실패
    if token_type != "setup" or phone_in_token != required_phone:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN 설정을 위한 임시 토큰이 유효하지 않습니다. OTP 인증을 다시 진행해 주세요."
        )
    return True
