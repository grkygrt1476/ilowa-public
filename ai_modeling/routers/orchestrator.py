from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from ai_modeling.orchestration import get_orchestrator
from ai_modeling.schemas.job_post_schema import JobPost, JobPostResponse
from ai_modeling.schemas.recommendation import RecommendationRequest

router = APIRouter(prefix="/pipeline", tags=["Orchestration"])


class RecommendationPipelineRequest(RecommendationRequest):
    previous_recommendations: Optional[List[Dict[str, Any]]] = None


@router.post("/recommend")
def pipeline_recommend(
    payload: RecommendationPipelineRequest,
    provider: Optional[str] = Query(default=None, description="사용할 AI Provider (naver/local)")
):
    orchestrator = get_orchestrator(provider)
    result = orchestrator.recommend(
        user_profile=payload.user_profile.dict(),
        intent=payload.intent or "",
        previous_recommendations=payload.previous_recommendations or [],
    )
    return result


@router.post("/post/voice", response_model=JobPostResponse)
async def pipeline_post_from_voice(
    audio: UploadFile = File(...),
    provider: Optional[str] = Query(default=None, description="사용할 AI Provider (naver/local)")
):
    orchestrator = get_orchestrator(provider)
    audio_bytes = await audio.read()
    result = orchestrator.create_post_from_voice_bytes(audio_bytes)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "추출 실패"))
    return JobPostResponse(
        success=True,
        post=JobPost(**result["post"]),
        message=result.get("message"),
        needs_clarification=result.get("needs_clarification"),
        missing_fields=result.get("missing_fields"),
        questions=result.get("questions"),
        session_id=result.get("session_id"),
        provider=orchestrator.provider_name,
    )


@router.post("/post/image", response_model=JobPostResponse)
async def pipeline_post_from_image(
    file: UploadFile = File(...),
    provider: Optional[str] = Query(default=None, description="사용할 AI Provider (naver/local)")
):
    orchestrator = get_orchestrator(provider)
    image_bytes = await file.read()
    result = orchestrator.create_post_from_image_bytes(image_bytes)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "추출 실패"))
    return JobPostResponse(
        success=True,
        post=JobPost(**result["post"]),
        message=result.get("message"),
        provider=orchestrator.provider_name,
    )


@router.post("/post/text", response_model=JobPostResponse)
async def pipeline_post_from_text(
    raw_text: str,
    provider: Optional[str] = Query(default=None, description="사용할 AI Provider (naver/local)")
):
    orchestrator = get_orchestrator(provider)
    result = orchestrator.create_post_from_text(raw_text)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "추출 실패"))
    return JobPostResponse(
        success=True,
        post=JobPost(**result["post"]),
        message=result.get("message"),
        provider=orchestrator.provider_name,
    )
