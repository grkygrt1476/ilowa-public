# ilowa/backend_api/app/api/v1/auth.py
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from backend_api.app.schemas import auth as auth_schemas
from backend_api.app.services.auth_service import AuthService
from backend_api.app.db.database import get_db
from backend_api.app.core.exceptions import IlowaException
from backend_api.app.core.security import verify_setup_token
from backend_api.app.core.config import settings
from backend_api.app.core.security import generate_otp_code
from fastapi import Body

# from backend_api.app.gateways import sens_client  # ← SENS 사용 안 함 (더미 모드)

router = APIRouter(
    prefix="/auth",
    tags=["Auth - 인증/회원"]
)

# 의존성 주입: DB 세션
DbSessionDep = Annotated[Session, Depends(get_db)]


# ----------------------------------------------------
# 1. /register/phone (가입 시작)
# ----------------------------------------------------
@router.post("/register/phone", response_model=auth_schemas.MessageResponse, status_code=status.HTTP_200_OK)
async def register_phone_start(req: auth_schemas.PhoneRequest):
    """
    REG_01: 전화번호 유효성을 확인하고 OTP 발송을 준비합니다.
    """
    return auth_schemas.MessageResponse(
        message=f"번호 {req.phone_number}가 확인되었습니다. OTP 발송을 위해 다음 단계로 진행해주세요."
    )


# ----------------------------------------------------
# 2. /otp/send (OTP 발송 — 더미 0000만 사용)
# ----------------------------------------------------
@router.post("/otp/send", response_model=auth_schemas.OTPRequestSuccess)
async def send_otp(req: auth_schemas.OTPRequest):
    """
    REG_01.5: OTP 코드 발송.
    - 실제 SENS는 사용하지 않고, 더미 모드로만 발송(콘솔 로그)합니다.
    - 코드 생성은 core.security.generate_otp_code()가 담당 (USE_DUMMY_SMS=true면 0000 고정)
    """
    # ✅ 여기서는 절대 req.otp_code/req.code를 보지 않음 (서버가 생성)
    code = generate_otp_code()

    # (선택) OTP 저장 (Redis/메모리 등)
    # await otp_store.save_code(req.phone_number, code, ttl=getattr(settings, "OTP_TTL_SEC", 180))

    # 발송 (더미 로그만)
    # 실제 SENS 호출은 막아둠
    # sent = sens_client.send_otp_sms(req.phone_number, code)
    print(f"[SMS SIMULATION] To: {req.phone_number}, Code: {code}")
    sent = True

    if not sent:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="SMS 발송 실패")

    return auth_schemas.OTPRequestSuccess(
        phone_number=req.phone_number,
        expires_in=getattr(settings, "OTP_TTL_SEC", 180),
        cooldown=getattr(settings, "OTP_COOLDOWN_SEC", 60),
        # message는 모델 기본값 사용 ("인증번호가 발송되었습니다.")
    )


# ----------------------------------------------------
# 3. /otp/verify (OTP 검증)
# ----------------------------------------------------
@router.post(
    "/otp/verify",
    response_model=auth_schemas.VerifiedResponse | auth_schemas.TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_otp_code(
    req: auth_schemas.OTPVerifyRequest,
    db: DbSessionDep,
):
    """
    REG_02/LG_02: OTP 코드를 검증합니다.
    - register: setup_token 반환 (PIN 설정으로 이동)
    - login: 최종 JWT 반환
    """
    try:
        # ⚠️ 더미(0000) 허용/실제 검증은 AuthService.verify_otp 내부에서 처리
        auth_service = AuthService(db)
        token_info = await run_in_threadpool(auth_service.verify_otp, req)

        if req.purpose == "register":
            return auth_schemas.VerifiedResponse(
                verified=True,
                setup_token=token_info.setup_token,
            )
        elif req.purpose == "login":
            return auth_schemas.TokenResponse(
                user_id=token_info.user_id,
                access_token=token_info.access_token,
                refresh_token=token_info.refresh_token,
                expires_in=token_info.expires_in,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="purpose는 'register' 또는 'login'이어야 합니다.",
            )

    except HTTPException as e:
        # 서비스에서 의도적으로 던진 4xx/5xx는 그대로 전달
        raise e
    except IlowaException as e:
        # 커스텀 예외는 HTTPException으로 변환(기본 400)
        raise HTTPException(status_code=getattr(e, "status_code", 400), detail=str(e))
    except Exception as e:
        print(f"OTP 인증 중 서버 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인증 코드 확인 중 오류 발생",
        )


# ----------------------------------------------------
# 5. /register/pin (PIN 설정 및 가입 완료)
# ----------------------------------------------------
@router.post("/register/pin", response_model=auth_schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
async def setup_pin_and_register(
    req: auth_schemas.PINSetRequest,
    db: DbSessionDep,
):
    """
    REG_04: Setup Token 검증 후 PIN 설정 및 최종 사용자 등록을 완료합니다.
    """
    # 1) Setup Token 검증
    verify_setup_token(req.setup_token, req.phone_number)

    auth_service = AuthService(db)
    try:
        # 2) 사용자 등록 및 PIN 저장 (토큰 반환)
        token_info = await run_in_threadpool(auth_service.register_user, req)
        return auth_schemas.TokenResponse(
            user_id=token_info.user_id,
            access_token=token_info.access_token,
            refresh_token=token_info.refresh_token,
            expires_in=token_info.expires_in,
        )
    
    except HTTPException as e:
        # 서비스 계층의 의도적 응답은 그대로 전달 (409 등)
        raise e
    except IlowaException as e:
        raise HTTPException(status_code=getattr(e, "status_code", 400), detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 등록 중 알 수 없는 오류 발생",
        )


# ----------------------------------------------------
# 6. /login/pin (PIN 로그인)
# ----------------------------------------------------
@router.post("/login/pin", response_model=auth_schemas.TokenResponse, status_code=status.HTTP_200_OK)
async def login_with_pin(
    req: auth_schemas.PINLoginRequest,  # PINLoginSchema가 없으므로 재사용
    db: DbSessionDep,
):
    """
    LG_01: PIN을 사용한 로그인 및 토큰 발급
    """
    auth_service = AuthService(db)
    try:
        token_info = await run_in_threadpool(auth_service.login_with_pin, req)
        return auth_schemas.TokenResponse(
            user_id=token_info.user_id,
            access_token=token_info.access_token,
            refresh_token=token_info.refresh_token,
            expires_in=token_info.expires_in,
        )
    except HTTPException as e:
        raise e
    except IlowaException as e:
        raise HTTPException(status_code=getattr(e, "status_code", 400), detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 알 수 없는 오류 발생",
        )


@router.post("/register/agreements", response_model=auth_schemas.MessageResponse)
async def accept_agreements(req: auth_schemas.AgreementsRequest | None = Body(default=None)):
    data = req or auth_schemas.AgreementsRequest()  # 빈 바디면 모두 False로 채움
    # TODO: 저장 로직(선택)
    return auth_schemas.MessageResponse(message="약관 동의가 완료되었습니다.")
