import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))

import tempfile
import uuid
from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
import uvicorn

#from routers.post_automation import router as post_router
from routers.post_create import router as post_create_router
from routers.orchestrator import router as orchestrator_router
#from routers.post_approval import router as approval_router
#from agents.graph_builder import build_graph
from agents.react_agent import ReActAgent
from schemas.recommendation import RecommendationRequest
from services.providers import get_ai_provider
from orchestration.pipeline import DEFAULT_CSV_PATH as ORCHESTRATOR_CSV_PATH

app = FastAPI(title="🤖 ReAct 기반 지능형 소일거리 추천 시스템")
#app.include_router(post_router, prefix="/post")
app.include_router(post_create_router, prefix="/post")
app.include_router(orchestrator_router)
#app.include_router(approval_router, prefix="/post")

# LangGraph 컴파일
#graph = build_graph()

DEFAULT_CSV_PATH = ORCHESTRATOR_CSV_PATH


def _normalize_provider_name(name: Optional[str]) -> str:
    value = name or os.getenv("AI_PROVIDER") or "naver"
    return value.strip().lower().replace("-", "_")


@lru_cache(maxsize=4)
def _react_agent_factory(provider_name: str) -> ReActAgent:
    provider = get_ai_provider(provider_name)
    return ReActAgent(DEFAULT_CSV_PATH, provider=provider)


def _get_react_agent(provider_name: Optional[str] = None) -> tuple[ReActAgent, str]:
    normalized = _normalize_provider_name(provider_name)
    return _react_agent_factory(normalized), normalized

# 세션 저장소
sessions: Dict[str, Dict[str, Any]] = {}


# ==================== 1단계: 초기 추천 (ReAct Agent) ====================
@app.post("/recommend")
def initial_recommend(
    request: RecommendationRequest,
    provider: Optional[str] = Query(default=None, description="사용할 AI Provider (예: naver, local)")
):
    """
    1차 추천: 사용자 프로필 기반 자동 추천
    
    🤖 ReAct Agent가 Thought → Action → Observation 루프를 통해
    최적의 추천을 자율적으로 생성합니다.
    """
    try:
        # 세션 생성
        session_id = str(uuid.uuid4())
        
        user_profile = request.user_profile.dict()
        
        print(f"\n{'='*60}")
        print(f"📋 초기 추천 요청 (Session: {session_id})")
        print(f"{'='*60}\n")
        
        react_agent, provider_name = _get_react_agent(provider)
        # ReAct Agent 직접 실행
        result = react_agent.run(
            user_profile=user_profile,
            intent=request.intent or ""
        )
        
        # 세션 저장
        sessions[session_id] = {
            "user_profile": user_profile,
            "recommendations": result.get("recommendations", []),
            "reasoning": result.get("reason", {}),
            "created_at": str(uuid.uuid4()),
            "provider_name": provider_name
        }
        
        return {
            "session_id": session_id,
            "user_profile": user_profile,
            "recommendations": result.get("recommendations", []),
            "reasoning_summary": {
                "iterations": result.get("reason", {}).get("iterations", 0),
                "thoughts_count": len(result.get("reason", {}).get("thoughts", [])),
                "actions_count": len(result.get("reason", {}).get("actions", []))
            },
            "message": "✅ ReAct 기반 초기 추천이 완료되었습니다. 음성으로 추가 요청을 할 수 있습니다.",
            "provider": provider_name
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 2단계: 음성 기반 재추천 (ReAct Agent) ====================
@app.post("/recommend/voice")
async def voice_recommend(
    session_id: str,
    audio_file: UploadFile = File(...)
):
    """
    2차 재추천: 음성 파일 업로드 → STT → ReAct Agent 재실행
    
    🎙️ 사용자의 음성 의도를 인식하여 ReAct Agent가
    프로필 + 추가 요청을 종합하여 재추천합니다.
    """
    try:
        # 세션 확인
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        session = sessions[session_id]
        provider_name = session.get("provider_name")
        react_agent, _ = _get_react_agent(provider_name)
        
        print(f"\n{'='*60}")
        print(f"🎙️  음성 기반 재추천 요청 (Session: {session_id})")
        print(f"{'='*60}\n")
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            content = await audio_file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # STT: 음성 → 텍스트
            provider = get_ai_provider(provider_name)
            stt_result = provider.transcribe_audio(tmp_path, lang="Kor")
            voice_text = stt_result.get("text", "")
            
            if not voice_text:
                raise HTTPException(status_code=400, detail="음성 인식에 실패했습니다.")
            
            print(f"🗣️  음성 인식 결과: {voice_text}\n")
            
            # ReAct Agent 재실행 (음성 의도 포함)
            # 이전 추천 결과를 전달하여 Agent가 맥락을 이해하도록 함
            previous_recs = session.get("recommendations", [])
            
            result = react_agent.run(
                user_profile=session["user_profile"],
                intent=voice_text,
                previous_recommendations=previous_recs  # 이전 추천 전달
            )
            
            # 세션 업데이트
            sessions[session_id] = {
                "user_profile": session["user_profile"],
                "recommendations": result.get("recommendations", []),
                "reasoning": result.get("reason", {}),
                "last_voice_intent": voice_text,
                "provider_name": provider_name
            }
            
            return {
                "session_id": session_id,
                "voice_text": voice_text,
                "recommendations": result.get("recommendations", []),
                "reasoning_summary": {
                    "iterations": result.get("reason", {}).get("iterations", 0),
                    "thoughts_count": len(result.get("reason", {}).get("thoughts", [])),
                    "actions_count": len(result.get("reason", {}).get("actions", []))
                },
                "message": f"✅ 음성 기반 재추천이 완료되었습니다. ('{voice_text}')",
                "provider": provider_name
            }
        
        finally:
            # 임시 파일 삭제
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 세션 조회 ====================
@app.get("/recommend/session/{session_id}")
def get_session(session_id: str):
    """현재 세션의 추천 결과 조회"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    session = sessions[session_id]
    
    return {
        "session_id": session_id,
        "user_profile": session.get("user_profile"),
        "recommendations": session.get("recommendations", []),
        "last_voice_intent": session.get("last_voice_intent", ""),
        "reasoning": session.get("reasoning", {}),
        "provider": session.get("provider_name")
    }


# ==================== 추론 과정 조회 (디버깅용) ====================
@app.get("/recommend/session/{session_id}/reasoning")
def get_reasoning(session_id: str):
    """
    세션의 ReAct 추론 과정 상세 조회
    (Thought → Action → Observation 루프 추적)
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    session = sessions[session_id]
    reasoning = session.get("reasoning", {})
    
    return {
        "session_id": session_id,
        "iterations": reasoning.get("iterations", 0),
        "thoughts": reasoning.get("thoughts", []),
        "actions": reasoning.get("actions", []),
        "observations": reasoning.get("observations", []),
        "provider": session.get("provider_name")
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
