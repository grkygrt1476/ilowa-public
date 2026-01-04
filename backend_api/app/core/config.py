# backend_api/app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict # pydantic-settings 임포트
from pydantic import model_validator
from typing import Optional
from datetime import timedelta
import random,os
from urllib.parse import quote_plus

# 0. OTP 더미 코드 생성 

def generate_otp_code(length: int = 6) -> str:
    # 더미 모드: 항상 0000
    if settings.USE_DUMMY_SMS:
        return settings.DUMMY_OTP_CODE  # "0000"

    # 실제 모드
    digits = "0123456789"
    return "".join(random.choice(digits) for _ in range(length))

# 1. 설정 클래스 정의
class Settings(BaseSettings):
    ENVIRONMENT: str = "local"
    USE_DUMMY_SMS: bool = False
    DUMMY_OTP_CODE: str = "0000"
    AI_PROVIDER: str = "naver"
    # 환경 변수 파일을 사용함을 명시 (.env 파일 사용 시)
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    # A. 데이터베이스 설정 (PostgreSQL)
    # env 파일이나 환경 변수에 DB_URL이 없으면 기본값(SQLite)을 사용합니다.
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    # B. JWT 보안 설정
    SECRET_KEY: str = "YOUR_HIGHLY_SECURE_SECRET_KEY_HERE"
    # python-jose 기반 토큰 발급 경로에서 별도 비밀키를 기대할 수 있으므로
    # 설정에 존재하지 않으면 SECRET_KEY를 재사용하도록 기본 None으로 둔다.
    JWT_SECRET: str | None = None
    ALGORITHM: str = "HS256"
    
    # C. Naver SENS (SMS) 설정
    SENS_ACCESS_KEY: str
    SENS_SECRET_KEY: str
    SENS_SERVICE_ID: str
    SENS_CALLING_NUMBER: str = "01000000000"

    # D. API 및 토큰 만료 시간
    API_V1_STR: str = "/api/v1"
    OTP_EXPIRATION_DELTA: timedelta = timedelta(minutes=3)  # 3분
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    @model_validator(mode="after")
    def apply_database_url(self):
        """DATABASE_URL이 비어 있으면 Postgres 환경변수 기반으로 작성한다."""
        db_url = (self.DATABASE_URL or "").strip()
        if db_url:
            self.DATABASE_URL = db_url
            return self

        if self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB:
            user = quote_plus(self.POSTGRES_USER)
            password = quote_plus(self.POSTGRES_PASSWORD)
            host = (self.POSTGRES_HOST or "db").strip() or "db"
            port = self.POSTGRES_PORT or 5432
            self.DATABASE_URL = (
                f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{self.POSTGRES_DB}"
            )
        else:
            self.DATABASE_URL = "sqlite:///./ilowa.db"
        return self
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

# 2. Settings 인스턴스 생성 (환경 변수 로드)
settings = Settings()

# JWT_SECRET이 비어 있다면 SECRET_KEY를 기본값으로 사용한다.
if not getattr(settings, "JWT_SECRET", None):
    settings.JWT_SECRET = settings.SECRET_KEY


# 3. FastAPI 의존성 주입을 위한 함수
def get_settings():
    """FastAPI의 Depends() 함수에서 사용할 설정 객체를 반환합니다."""
    return settings

# 4. JWT 생성 유틸리티 함수 (security.py에서 사용됨)
# 이전에 임시로 main.py에 있던 함수들을 settings 객체에서 접근하도록 수정하거나,
# security.py에서 이 settings 객체를 임포트하여 사용하도록 연결합니다.


# 5. 재가입 허용 설정
def _as_bool(v: str, default=False):
    if v is None:
        return default
    return str(v).strip().lower() in ("1","true","t","yes","y","on")

ALLOW_REREGISTER_ON_EXISTING = _as_bool(
    os.getenv("ALLOW_REREGISTER_ON_EXISTING"),
    default=False,  # 운영 기본 False 권장
)
