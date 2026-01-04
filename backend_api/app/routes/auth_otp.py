# app/routes/auth_otp.py
"""
OTP send/verify endpoints for phone-based auth.

- Accepts either `phone` (E.164, e.g., +821012345678) or `phone_number` (local KR 010xxxxxxxx).
- Falls back to an in-memory store when Redis is unavailable (demo-safe).
- Supports MOCK SMS mode via env: MOCK_SMS=true (default).
- Allows a demo bypass code "000000" when OTP_ALLOW_DUMMY=true (default true).

Required env (recommended):
  REDIS_URL                 -> your Redis connection string (if you use Redis)
  MOCK_SMS=true|false       -> mock SMS mode (default true)
  OTP_TTL_SEC=180           -> OTP validity seconds (default 180)
  OTP_LEN=6                 -> OTP digits (default 6)
  OTP_ALLOW_DUMMY=true|false-> allow "000000" as a bypass code (default true)
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import random
import re
import traceback
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

# ------------------------------------------------------------
# Router
# ------------------------------------------------------------
router = APIRouter(prefix="/api/v1/auth/otp", tags=["auth/otp"])
logger = logging.getLogger("otp")

# ------------------------------------------------------------
# Environment / Defaults
# ------------------------------------------------------------
MOCK_SMS: bool = os.getenv("MOCK_SMS", "true").lower() == "true"
OTP_TTL_SEC: int = int(os.getenv("OTP_TTL_SEC", "180"))
OTP_LEN: int = int(os.getenv("OTP_LEN", "6"))
OTP_ALLOW_DUMMY: bool = os.getenv("OTP_ALLOW_DUMMY", "true").lower() == "true"

# ------------------------------------------------------------
# Optional Redis (import/assign your client elsewhere if needed)
#   Ex) from app.core.redis import redis  # aioredis client
#   Here we try to import; if not available, we just keep `redis=None`.
# ------------------------------------------------------------
try:
    from app.core.redis import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # will fallback to memory

# ------------------------------------------------------------
# In-memory fallback storage (for demo mode)
# MEM_STORE keys: "otp:{e164}" -> (code, expire_ts)
#                  "otp:rl:{e164}" -> (1, expire_ts)  # for rate limiting
#                  "otp:st:{e164}" -> (setup_token, expire_ts)
# ------------------------------------------------------------
MEM_STORE: dict[str, Tuple[str, float]] = {}

def _mem_set(key: str, value: str, ex: int) -> None:
    MEM_STORE[key] = (value, asyncio.get_event_loop().time() + ex)

def _mem_get(key: str) -> Optional[str]:
    tup = MEM_STORE.get(key)
    if not tup:
        return None
    value, expire = tup
    if asyncio.get_event_loop().time() > expire:
        MEM_STORE.pop(key, None)  # expired
        return None
    return value

def _mem_exists(key: str) -> bool:
    return _mem_get(key) is not None

# ------------------------------------------------------------
# Utils
# ------------------------------------------------------------
def to_e164_kr(raw: Optional[str]) -> Optional[str]:
    """
    Convert KR local numbers (010xxxxxxxx) to E.164 (+8210xxxxxxx).
    If already E.164 or '+82...', return as is.
    """
    if not raw:
        return None
    s = str(raw).strip()
    if s.startswith("+"):
        # naive allow
        return s
    digits = re.sub(r"\D", "", s)
    if digits.startswith("82"):
        return f"+{digits}"
    if digits.startswith("010") and len(digits) == 11:
        return f"+82{digits[1:]}"
    # Could add more rules for 02-xxxx-xxxx, etc., if needed.
    return None

def mask_phone(e164: str) -> str:
    return e164[:-6] + "******" if len(e164) >= 6 else "********"

def make_setup_token() -> str:
    return base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")

async def _rate_limit_check_and_set(e164: str) -> None:
    key_rl = f"otp:rl:{e164}"
    try:
        if redis:
            exists = await redis.exists(key_rl)
            if exists:
                raise HTTPException(429, detail="too_many_requests")
            await redis.set(key_rl, "1", ex=60)
        else:
            if _mem_exists(key_rl):
                raise HTTPException(429, detail="too_many_requests")
            _mem_set(key_rl, "1", ex=60)
    except HTTPException:
        raise
    except Exception:
        logger.exception("[OTP RL] Redis error → fallback to memory")
        if _mem_exists(key_rl):
            raise HTTPException(429, detail="too_many_requests")
        _mem_set(key_rl, "1", ex=60)

async def _store_code(e164: str, code: str, ttl: int) -> None:
    key = f"otp:{e164}"
    try:
        if redis:
            await redis.set(key, code, ex=ttl)
        else:
            _mem_set(key, code, ex=ttl)
    except Exception:
        logger.exception("[OTP SET] Redis error → fallback to memory")
        _mem_set(key, code, ex=ttl)

async def _load_code(e164: str) -> Optional[str]:
    key = f"otp:{e164}"
    try:
        if redis:
            v = await redis.get(key)
            return v.decode() if v else None
        return _mem_get(key)
    except Exception:
        logger.exception("[OTP GET] Redis error → fallback to memory")
        return _mem_get(key)

async def _store_setup_token(e164: str, token: str, ttl: int) -> None:
    key = f"otp:st:{e164}"
    try:
        if redis:
            await redis.set(key, token, ex=ttl)
        else:
            _mem_set(key, token, ex=ttl)
    except Exception:
        logger.exception("[SETUP TOKEN SET] Redis error → fallback to memory")
        _mem_set(key, token, ex=ttl)

async def _load_setup_token(e164: str) -> Optional[str]:
    key = f"otp:st:{e164}"
    try:
        if redis:
            v = await redis.get(key)
            return v.decode() if v else None
        return _mem_get(key)
    except Exception:
        logger.exception("[SETUP TOKEN GET] Redis error → fallback to memory")
        return _mem_get(key)

# ------------------------------------------------------------
# Schemas
# ------------------------------------------------------------
class OtpSendReq(BaseModel):
    phone: Optional[str] = None
    phone_number: Optional[str] = Field(default=None, description="Local KR format 010xxxxxxxx")
    purpose: str = Field(..., regex="^(register|login)$")

class OtpSendRes(BaseModel):
    ttl: int
    mask: str

class OtpVerifyReq(BaseModel):
    phone: Optional[str] = None
    phone_number: Optional[str] = None
    code: str = Field(..., min_length=6, max_length=6)
    purpose: str = Field(..., regex="^(register|login)$")

class OtpVerifyRes(BaseModel):
    setup_token: str

# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@router.post("/send", response_model=OtpSendRes)
async def send_otp(req: OtpSendReq, request: Request):
    """
    Send OTP code to the given phone.
    - Rate limited: 1 per minute per phone.
    - Stores OTP with TTL=OTP_TTL_SEC.
    - MOCK mode logs code to server logs.
    """
    try:
        raw = req.phone or req.phone_number or ""
        e164 = to_e164_kr(raw)
        if not e164:
            raise HTTPException(400, detail="invalid_phone")
        if req.purpose not in ("register", "login"):
            raise HTTPException(400, detail="invalid_purpose")

        # Rate limit
        await _rate_limit_check_and_set(e164)

        # Create & store code
        code = f"{random.randint(0, 10**OTP_LEN - 1):0{OTP_LEN}d}"
        await _store_code(e164, code, OTP_TTL_SEC)

        # Send SMS (mock by default)
        msg = f"[잡있으] 인증번호 {code} (유효 {OTP_TTL_SEC//60}분)"
        if MOCK_SMS:
            logger.info(f"[MOCK SMS] to={e164} code={code} msg='{msg}'")
            await asyncio.sleep(0.05)
        else:
            # TODO: integrate with your provider (Twilio, SENS, Toast, etc.)
            # Make sure to handle provider exceptions and map to 502 if needed.
            raise NotImplementedError("SMS provider not configured")

        return OtpSendRes(ttl=OTP_TTL_SEC, mask=mask_phone(e164))

    except HTTPException:
        raise
    except Exception:
        body = await request.body()
        logger.error(f"[OTP SEND ERROR] path={request.url.path} body={body.decode('utf-8','ignore')}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, detail="internal_error")

@router.post("/verify", response_model=OtpVerifyRes)
async def verify_otp(req: OtpVerifyReq, request: Request):
    """
    Verify OTP code.
    - If valid, issues a short-lived `setup_token` stored with same TTL.
    - Allows demo bypass with "000000" when OTP_ALLOW_DUMMY=true.
    """
    try:
        raw = req.phone or req.phone_number or ""
        e164 = to_e164_kr(raw)
        if not e164:
            raise HTTPException(400, detail="invalid_phone")
        if req.purpose not in ("register", "login"):
            raise HTTPException(400, detail="invalid_purpose")

        expected = await _load_code(e164)
        ok = (expected is not None and expected == req.code) or (OTP_ALLOW_DUMMY and req.code == "000000")
        if not ok:
            raise HTTPException(400, detail="invalid_code")

        setup_token = make_setup_token()
        await _store_setup_token(e164, setup_token, OTP_TTL_SEC)

        # (Optional) create a pending user row here if your flow needs it

        return OtpVerifyRes(setup_token=setup_token)

    except HTTPException:
        raise
    except Exception:
        body = await request.body()
        logger.error(f"[OTP VERIFY ERROR] path={request.url.path} body={body.decode('utf-8','ignore')}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, detail="internal_error")
