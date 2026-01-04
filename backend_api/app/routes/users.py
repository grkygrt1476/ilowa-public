# app/routes/users.py (부분)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.auth import get_current_user  # JWT에서 user_id 추출
from app.core.users import update_profile, get_profile

router = APIRouter(prefix="/api/v1/users", tags=["users"])

class ProfilePatch(BaseModel):
    nickname: str | None = None
    location: str | None = None
    preferences: dict | None = None

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return await get_profile(user.user_id)

@router.patch("/me")
async def patch_me(req: ProfilePatch, user=Depends(get_current_user)):
    updated = await update_profile(user.user_id, req.model_dump(exclude_none=True))
    return {"user_id": user.user_id, "nickname": updated.get("nickname"), "updated_at": updated.get("updated_at")}
