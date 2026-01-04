from fastapi import APIRouter, UploadFile, File, HTTPException, Query
import tempfile, os
from agents.posting_agent import PostingAutomationAgent
from schemas.job_post_schema import JobPostResponse, JobPost
from services.providers import get_ai_provider
from typing import Dict, Any, Optional

router = APIRouter()

# 대화형 세션 저장소
voice_sessions: Dict[str, Dict[str, Any]] = {}


def _get_agent(provider_name: Optional[str] = None) -> PostingAutomationAgent:
    """Instantiate a posting agent for the requested provider."""
    provider = get_ai_provider(provider_name)
    return PostingAutomationAgent(provider=provider)

@router.post("/create/voice", response_model=JobPostResponse)
async def create_post_from_voice(
    audio: UploadFile = File(...),
    provider: Optional[str] = Query(default=None, description="사용할 AI Provider (naver/local)")
):
    agent = _get_agent(provider)
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            data = await audio.read()
            tmp.write(data)
            path = tmp.name
        try:
            result = agent.extract_from_voice(path)
        finally:
            if os.path.exists(path):
                os.remove(path)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "추출 실패"))
        
        post = result["post"]
        # 빈 필드 체크
        missing_check = agent.check_missing_fields(post)
        
        if missing_check["needs_clarification"]:
            # 세션 생성
            import uuid
            session_id = str(uuid.uuid4())
            voice_sessions[session_id] = {
                "post": post,
                "missing": missing_check,
                "provider_name": getattr(agent, "provider_name", provider or "naver")
            }
            
            return {
                "success": True,
                "post": JobPost(**post),
                "session_id": session_id,
                "needs_clarification": True,
                "missing_fields": missing_check["missing_fields"],
                "questions": missing_check["questions"],
                "message": "일부 정보가 부족합니다. 아래 질문에 답변해주세요.",
                "provider": getattr(agent, "provider_name", provider or "naver")
            }
        
        return {
            "success": True,
            "post": JobPost(**post),
            "provider": getattr(agent, "provider_name", provider or "naver")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create/voice/clarify")
async def clarify_post(session_id: str, audio: UploadFile = File(...)):
    """빈 필드 보완을 위한 추가 음성 입력 (한 번만 받고 종료)"""
    if session_id not in voice_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    session = voice_sessions[session_id]

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            data = await audio.read()
            tmp.write(data)
            path = tmp.name
        try:
            provider_name = session.get("provider_name")
            provider = get_ai_provider(provider_name)
            stt = provider.transcribe_audio(path, lang="Kor")
            text = stt.get("text", "").strip()
        finally:
            if os.path.exists(path):
                os.remove(path)
        
        if not text:
            raise HTTPException(status_code=400, detail="음성 인식 실패")
        
        # 기존 post에 병합
        provider_name = session.get("provider_name")
        agent = _get_agent(provider_name)
        merged_post = agent.merge_additional_input(session["post"], text)
        
        # 세션 삭제 (한 번만 추가 입력 받고 종료)
        del voice_sessions[session_id]
        
        return {
            "success": True,
            "post": JobPost(**merged_post),
            "needs_clarification": False,
            "message": "공고 생성이 완료되었습니다. 필요시 직접 편집하실 수 있습니다.",
            "provider": getattr(agent, "provider_name", provider_name or "naver")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create/image", response_model=JobPostResponse)
async def create_post_from_image(
    file: UploadFile = File(...),
    provider: Optional[str] = Query(default=None, description="사용할 AI Provider (naver/local)")
):
    try:
        image_bytes = await file.read()
        agent = _get_agent(provider)
        result = agent.extract_from_image_bytes(image_bytes)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "추출 실패"))
        return {
            "success": True,
            "post": JobPost(**result["post"]),
            "provider": getattr(agent, "provider_name", provider or "naver")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/create/text", response_model=JobPostResponse)
# async def create_post_from_text(raw: str):
#     try:
#         result = agent.extract_from_text(raw)
#         if not result.get("success"):
#             raise HTTPException(status_code=400, detail=result.get("message", "추출 실패"))
#         return {"success": True, "post": JobPost(**result["post"])}
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
