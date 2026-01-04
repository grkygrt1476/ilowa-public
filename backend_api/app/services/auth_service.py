# backend_api/app/services/auth_service.py

import base64
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from backend_api.app.core import security
from backend_api.app.core.config import settings
from backend_api.app.core.hashers import Argon2Hasher  # ← 순환 import 방지 (security가 아닌 hashers)
from backend_api.app.core.exceptions import (
    OTPInvalidException,
    OTPCodeExpiredException,
    UserNotFoundException,
)
from backend_api.app.db.models.auth import (
    User,
    OTPVerificationRequest,
    UserRole,
)
from backend_api.app.schemas import auth as auth_schemas
from backend_api.app.schemas.auth import (
    TokenResponse,
    OTPRequest,
    OTPVerifyRequest,
    PINSetRequest,
    PINLoginRequest,
)

# -------------------------------
# 더미 SMS 전송 (로컬/더미 모드)
# -------------------------------
def send_otp_sms(phone_number: str, code: str) -> bool:
    """
    실제 SENS는 사용하지 않고, 개발 모드에선 콘솔 로그만 남긴다.
    """
    # 실제 연동은 주석 처리
    # from backend_api.app.gateways import sens_client
    # sens_client.send_sms(...)
    print(f"[SMS SIMULATION] To: {phone_number}, Code: {code}")
    return True


@dataclass
class SimpleTokenInfo:
    # register 플로우
    setup_token: Optional[str] = None
    # login 플로우
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: int = 0


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.pin_hasher = Argon2Hasher()  # hash_pin / verify_pin 지원

    # ----------------------------------------------------
    # 1) OTP 요청/전송
    # ----------------------------------------------------
    def request_otp(self, phone_number: str, purpose: str) -> bool:
        """
        OTP 코드 생성/저장 및 (더미) 발송.
        라우터 예시: await run_in_threadpool(auth_service.request_otp, req.phone_number, req.purpose)
        """
        # 1) 쿨다운(60초)
        last_req_stmt = (
            select(OTPVerificationRequest)
            .where(OTPVerificationRequest.phone_number == phone_number)
            .order_by(OTPVerificationRequest.created_at.desc())
        )
        latest_otp_req = self.db.exec(last_req_stmt).first()
        if latest_otp_req and (datetime.now(timezone.utc) - latest_otp_req.created_at).total_seconds() < 60:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="너무 자주 요청하셨습니다. 잠시 후 다시 시도해 주세요 (60초 쿨다운).",
            )

        # 2) OTP 코드 생성 (더미 모드면 .env의 DUMMY_OTP_CODE 사용)
        otp_code = security.generate_otp_code()  # 기본 6자리

        # 3) DB 저장
        expiration_delta: timedelta = getattr(settings, "OTP_EXPIRATION_DELTA", timedelta(minutes=3))
        new_otp_req = OTPVerificationRequest(
            phone_number=phone_number,
            otp_code=otp_code,  # 해시 없이 저장(개발용). 운영 시에는 해시를 권장.
            purpose=purpose,
            expires_at=datetime.now(timezone.utc) + expiration_delta,
        )
        self.db.add(new_otp_req)
        self.db.commit()
        self.db.refresh(new_otp_req)

        # 4) (더미) 발송
        send_otp_sms(phone_number, otp_code)
        return True

    # ----------------------------------------------------
    # 2) OTP 검증
    # ----------------------------------------------------
    def verify_otp(self, req: OTPVerifyRequest) -> SimpleTokenInfo:
        phone = req.phone_number
        code = req.code  # alias=otp_code 라도 여기서는 code로 접근

        # 0) 더미 모드: .env와 일치하면 즉시 통과
        if getattr(settings, "USE_DUMMY_SMS", False) and code == getattr(settings, "DUMMY_OTP_CODE", "000000"):
            return self._issue_after_otp(req)

        # 1) 최신 유효 OTP 조회 (만료 X, 미사용)
        stmt = (
            select(OTPVerificationRequest)
            .where(
                OTPVerificationRequest.phone_number == phone,
                OTPVerificationRequest.expires_at > datetime.now(timezone.utc),
                OTPVerificationRequest.is_used == False,
            )
            .order_by(OTPVerificationRequest.created_at.desc())
        )
        latest = self.db.exec(stmt).first()

        if not latest:
            # 최근 요청이 있긴 한지 확인해서 만료/미존재 케이스 구분(Optional)
            raise OTPCodeExpiredException()

        # 2) 코드 비교 (운영 시에는 해시 비교 권장)
        if latest.otp_code != code:
            self._handle_otp_failure(latest)
            raise OTPInvalidException()

        # 3) 사용 처리
        latest.is_used = True
        self.db.add(latest)
        self.db.commit()
        self.db.refresh(latest)

        # 4) 목적별 후속 처리
        return self._issue_after_otp(req)

    def _issue_after_otp(self, req: OTPVerifyRequest) -> SimpleTokenInfo:
        if req.purpose == "register":
            return self._issue_setup_token(req.phone_number)
        elif req.purpose == "login":
            return self._issue_login_tokens(req.phone_number)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="purpose는 'register' 또는 'login'이어야 합니다.",
            )

    # ---------- setup_token 발급 ----------
    def _issue_setup_token(self, phone_number: str) -> SimpleTokenInfo:
        """
        PIN 설정을 위한 단기(setup) 토큰 발급.
        security 모듈에 함수가 있으면 사용, 없으면 개발용 폴백 토큰 발급.
        """
        token = None

        for fn in ("create_setup_token", "issue_setup_token", "make_setup_token"):
            if hasattr(security, fn) and callable(getattr(security, fn)):
                token = getattr(security, fn)(phone_number)
                break

        if token is None:
            # jose가 있으면 JWT, 없으면 간단 토큰
            try:
                from jose import jwt
                now = datetime.utcnow()
                payload = {
                    "sub": f"setup:{phone_number}",
                    "phone": phone_number,
                    "type": "setup",
                    "iat": int(now.timestamp()),
                    "exp": int((now + timedelta(minutes=10)).timestamp()),
                    "iss": "ilowa",
                }
                secret = getattr(settings, "JWT_SECRET", None) or settings.SECRET_KEY
                token = jwt.encode(payload, secret, algorithm=getattr(settings, "JWT_ALGORITHM", "HS256"))
            except Exception:
                raw = f"setup|{phone_number}|{int(datetime.utcnow().timestamp())}|{os.urandom(6).hex()}"
                token = "setup." + base64.urlsafe_b64encode(raw.encode()).decode()

        return SimpleTokenInfo(setup_token=token)

    # ---------- access/refresh 발급 ----------
    def _issue_login_tokens(self, phone_number: str) -> SimpleTokenInfo:
        user = self._get_user_by_phone(phone_number)
        if not user:
            raise UserNotFoundException()

        # security 모듈에 발급기가 있으면 우선 사용
        for fn in ("issue_access_refresh_tokens", "create_access_refresh_tokens", "make_access_refresh_tokens"):
            if hasattr(security, fn) and callable(getattr(security, fn)):
                t = getattr(security, fn)(user_id=str(user.user_id if hasattr(user, "user_id") else user.id))
                return SimpleTokenInfo(
                    user_id=str(user.user_id if hasattr(user, "user_id") else user.id),
                    access_token=t["access_token"],
                    refresh_token=t["refresh_token"],
                    expires_in=int(t.get("expires_in", getattr(settings, "ACCESS_TOKEN_TTL_SEC", 3600))),
                )

        # jose가 있으면 JWT, 없으면 간단 토큰
        try:
            from jose import jwt
            now = datetime.utcnow()
            user_id_str = str(user.user_id if hasattr(user, "user_id") else user.id)
            access_ttl = int(getattr(settings, "ACCESS_TOKEN_TTL_SEC", 3600))
            refresh_days = int(getattr(settings, "REFRESH_TOKEN_TTL_DAYS", 14))
            algo = getattr(settings, "JWT_ALGORITHM", "HS256")
            secret = getattr(settings, "JWT_SECRET", None) or settings.SECRET_KEY

            access_payload = {
                "sub": user_id_str,
                "type": "access",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(seconds=access_ttl)).timestamp()),
                "iss": "ilowa",
                "aud": "ilowa.api",
            }
            refresh_payload = {
                "sub": user_id_str,
                "type": "refresh",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(days=refresh_days)).timestamp()),
                "iss": "ilowa",
                "aud": "ilowa.api",
            }
            access_token = jwt.encode(access_payload, secret, algorithm=algo)
            refresh_token = jwt.encode(refresh_payload, secret, algorithm=algo)
        except Exception:
            access_token = "acc." + base64.urlsafe_b64encode(os.urandom(24)).decode()
            refresh_token = "ref." + base64.urlsafe_b64encode(os.urandom(24)).decode()
            access_ttl = int(getattr(settings, "ACCESS_TOKEN_TTL_SEC", 3600))

        return SimpleTokenInfo(
            user_id=str(user.user_id if hasattr(user, "user_id") else user.id),
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=access_ttl,
        )

    # ----------------------------------------------------
    # 3) PIN 설정 + 최종 가입
    # ----------------------------------------------------
    def register_user(self, req: PINSetRequest) -> TokenResponse:
        """
        PIN 설정 후 회원가입 완료 (Setup Token 필요)
        요구사항(테스트 버전): 이미 가입된 번호여도 실패시키지 말고 '성공' 처리.
        - 기존 사용자 + PIN 있음: 201 성공으로 통과(토큰 발급), message만 안내
        - 기존 사용자 + PIN 없음: PIN 세팅 후 201 성공
        - 사용자 없음: 신규 생성 후 201 성공
        """
        # 1) Setup Token 검증
        if not security.verify_setup_token(req.setup_token, req.phone_number):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 가입 토큰입니다. OTP 인증을 다시 진행해 주세요.",
            )

        # 2) 기존 사용자 조회
        user = self._get_user_by_phone(req.phone_number)

        # 3) PIN 해싱 (필요 시 사용)
        hashed_pin = self.pin_hasher.hash_pin(req.pin)

        try:
            if user:
                if getattr(user, "pin_hash", None):
                    # ✅ 이미 가입된 사용자도 '성공' 처리 (PIN은 그대로 유지)
                    new_user = user
                    info_msg = "이미 가입된 사용자입니다. PIN 로그인을 이용해 주세요."
                else:
                    # 번호는 있으나 PIN 미설정 → PIN만 세팅 후 성공
                    user.pin_hash = hashed_pin
                    if user.nickname is None:
                        user.nickname = "일로와_" + req.phone_number[-4:]
                    if user.role is None:
                        user.role = UserRole.JOB_SEEKER
                    if user.point_balance is None:
                        user.point_balance = 0
                    if user.is_verified is None:
                        user.is_verified = True
                    user.is_onboarding_complete = False
                    user.updated_at = datetime.utcnow()
                    self.db.add(user)
                    self.db.commit()
                    self.db.refresh(user)
                    new_user = user
                    info_msg = "PIN 설정이 완료되었습니다."
            else:
                # 신규 생성
                new_user = User(
                    phone_number=req.phone_number,
                    pin_hash=hashed_pin,
                    is_verified=True,
                    nickname="일로와_" + req.phone_number[-4:],
                    location="",
                    role=UserRole.JOB_SEEKER,
                    point_balance=0,
                    is_onboarding_complete=False,
                    # 🔹 NOT NULL 타임스탬프 채우기
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                   # (권장) NULL 방지
                    preferences={},
                )
                self.db.add(new_user)
                self.db.commit()
                self.db.refresh(new_user)
                info_msg = "회원가입과 PIN 설정이 완료되었습니다."
        except IntegrityError:
            self.db.rollback()
            # 이 케이스는 거의 신규 생성 시에만 발생
            # 요구사항상 실패로 막지 않고, 기존 사용자 조회로 재시도해 성공 흐름을 유지하려면:
            existing = self._get_user_by_phone(req.phone_number)
            if existing:
                new_user = existing
                info_msg = "이미 가입된 사용자입니다. PIN 로그인을 이용해 주세요."
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="이미 존재하는 전화번호입니다.",
                )

        # 4) 자동 로그인 토큰 발급 (항상 성공 흐름)
        access_token = security.create_access_token(new_user.user_id)
        refresh_token = security.create_refresh_token(new_user.user_id)

        return TokenResponse(
            user_id=new_user.user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)) * 60,
            message=info_msg,  # ← "이미 가입된 사용자입니다..." 그대로 내려줌(성공)
        )

    # ----------------------------------------------------
    # 4) PIN 로그인
    # ----------------------------------------------------
    def login_with_pin(self, req: PINLoginRequest) -> TokenResponse:
        """
        PIN 로그인
        """
        user = self._get_user_by_phone(req.phone_number)
        if not user or not getattr(user, "pin_hash", None):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="전화번호 또는 PIN이 올바르지 않습니다.",
            )

        if not self.pin_hasher.verify_pin(user.pin_hash, req.pin):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="전화번호 또는 PIN이 올바르지 않습니다.",
            )

        access_token = security.create_access_token(user.user_id)
        refresh_token = security.create_refresh_token(user.user_id)

        # user.last_login = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.commit()

        return TokenResponse(
            user_id=user.user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)) * 60,
            message="PIN 로그인에 성공했습니다.",
        )

    # ----------------------------------------------------
    # 5) 내부 유틸/실패 누적
    # ----------------------------------------------------
    def _get_user_by_phone(self, phone_number: str) -> Optional[User]:
        stmt = select(User).where(User.phone_number == phone_number)
        return self.db.exec(stmt).first()

    def _handle_otp_failure(self, latest_otp_req: Optional[OTPVerificationRequest]) -> None:
        if latest_otp_req:
            latest_otp_req.attempts_count += 1
            if latest_otp_req.attempts_count > 5:
                latest_otp_req.is_used = True
            self.db.add(latest_otp_req)
            self.db.commit()
