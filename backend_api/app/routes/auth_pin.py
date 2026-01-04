# app/routes/auth_pin.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import os, bcrypt

from app.core.redis import redis
from app.core.phone import to_e164_kr
from app.core.security import create_tokens
from app.core.users import upsert_user_with_pin, get_user_by_phone, verify_pin

router = APIRouter(prefix="/api/v1/auth", tags=["auth/pin"])

class RegisterPinReq(BaseModel):
    phone: Optional[str] = None
    phone_number: Optional[str] = None
    pin: str = Field(..., min_length=4, max_length=4)
    confirm_pin: str = Field(..., min_length=4, max_length=4)
    setup_token: str

class LoginPinReq(BaseModel):
    phone: Optional[str] = None
    phone_number: Optional[str] = None
    pin: str = Field(..., min_length=4, max_length=4)

@router.post("/register/pin")
async def register_pin(req: RegisterPinReq):
    raw = req.phone or req.phone_number or ""
    e164 = to_e164_kr(raw)
    if not e164:
        raise HTTPException(400, detail="invalid_phone", headers={"x-error-code":"invalid_phone"})
    if req.pin != req.confirm_pin:
        raise HTTPException(422, detail="pin_mismatch", headers={"x-error-code":"pin_mismatch"})

    st = await redis.get(f"otp:st:{e164}")
    if not st or st.decode()!=req.setup_token:
        raise HTTPException(401, detail="setup_token_invalid", headers={"x-error-code":"setup_token_invalid"})

    user = await upsert_user_with_pin(e164, req.pin)  # 내부에서 bcrypt hash 저장
    access, refresh = await create_tokens(user_id=user.id, phone=e164)
    return {"access_token": access, "refresh_token": refresh, "user_id": user.id}

@router.post("/login/pin")
async def login_pin(req: LoginPinReq):
    raw = req.phone or req.phone_number or ""
    e164 = to_e164_kr(raw)
    if not e164:
        raise HTTPException(400, detail="invalid_phone", headers={"x-error-code":"invalid_phone"})

    user = await get_user_by_phone(e164)
    if not user or not await verify_pin(user, req.pin):
        raise HTTPException(401, detail="invalid_credentials", headers={"x-error-code":"invalid_credentials"})

    access, refresh = await create_tokens(user_id=user.id, phone=e164)
    return {"access_token": access, "refresh_token": refresh, "user_id": user.id}
