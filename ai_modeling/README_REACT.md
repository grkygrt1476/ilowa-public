# 🤖 ReAct 기반 지능형 소일거리 추천 시스템

이 시스템은 **ReAct (Reasoning + Acting) 패턴**을 기반으로 한 진정한 AI Agent로,
시니어 맞춤 소일거리 공고를 지능적으로 추천합니다.

## 🎯 핵심 특징

### ReAct Agent의 자율적 추론
Agent는 Thought → Action → Observation 루프를 통해 자율적으로 최적의 추천을 찾습니다:

1. **💭 Thought (생각)**: 현재 상황 분석
   - 사용자 프로필과 요청 분석
   - 이전 시도 결과 평가
   - 다음 전략 결정

2. **🔧 Action (행동)**: 최적의 Tool 선택 및 실행
   - RAG 검색, 지역 기반 검색, 경험 기반 검색 등 8가지 Tool
   - 상황에 맞는 Tool 자동 선택
   - 하이브리드 검색, 필터링 등 복합 전략

3. **📊 Observation (관찰)**: 결과 평가 및 검증
   - 결과 품질 검증
   - 충분한 결과 획득 시 종료
   - 부족하면 다른 전략 자동 시도

### 다중 Tool 시스템
8가지 검색/필터링 Tool을 상황에 맞게 조합:

```
- rag_search: Embedding 기반 의미론적 검색
- region_specific_search: 지역 기반 정확한 검색
- experience_based_search: 경험 키워드 기반 검색
- price_filtered_search: 시급 범위 필터링
- hybrid_search: RAG + 프로필 필터링 결합
- latest_jobs: 최신 공고
- profile_match_filter: 프로필 기반 필터링
- validate_recommendations: 결과 품질 검증
```

## 프로젝트 구조
```
ai_modeling/
├─ agents/
│  ├─ react_agent.py           # 🤖 ReAct Agent (핵심 엔진)
│  ├─ graph_builder.py         # LangGraph workflow 정의
│  ├─ tools/
│  │  ├─ csv_rag_tool.py      # CSV 기반 RAG 도구
│  │  └─ toolkit.py           # 8가지 Tool 구현 (NEW)
│  ├─ supervisor_agent.py      # [레거시] 기본 계획 에이전트
│  └─ recommender_agent.py     # [레거시] 기본 추천 에이전트
├─ data/
│  └─ new_work_with_embeddings.csv # 소일거리 공고 + embedding
├─ models/
│  └─ job_model.py
├─ routers/
│  └─ post_automation.py       # OCR → LLM → 저장 파이프라인
├─ schemas/
│  └─ post_automation_schema.py
├─ services/
│  ├─ clova_ocr.py            # CLOVA OCR
│  ├─ clova_llm.py            # CLOVA LLM
│  ├─ clova_embedding.py      # CLOVA Embedding
│  ├─ clova_stt.py            # CLOVA STT
│  └─ html_parser.py          # OCR HTML 파싱
├─ main.py                    # FastAPI 메인 (ReAct 통합)
├─ test_react_agent.py        # 테스트 스크립트 (NEW)
└─ sample/
   ├─ test_post.png
   └─ test_voice.mp3
```

## 🚀 설치 및 실행

### 필수 패키지 설치
```bash
pip install -r requirements.txt
```

### 환경 변수 설정
```bash
# CLOVA OCR
CLOVA_OCR_URL="your_clova_ocr_url"
CLOVA_OCR_SECRET="your_clova_ocr_secret"

# CLOVA STT
CLOVA_STT_URL="your_clova_stt_url"
CLOVA_STT_SECRET="your_clova_stt_secret"

# CLOVA LLM (Reasoning용)
CLOVA_LLM_URL="your_clova_llm_url"
CLOVA_LLM_API_KEY="your_clova_llm_api_key"

# 서비스
PORT=8000
```

### FastAPI 서버 실행
```bash
# 개발 모드 (자동 리로드)
uvicorn main:app --reload --port 8000

# 프로덕션
uvicorn main:app --host 0.0.0.0 --port 8000
```

Swagger UI: http://127.0.0.1:8000/docs

### ReAct Agent 테스트
```bash
python test_react_agent.py
```

## 📡 API 사용 가이드

### 1. 초기 추천 (1차 추천)
```bash
POST /recommend

요청:
{
  "user_profile": {
    "nickname": "김할머니",
    "regions": ["서울"],
    "days": ["월", "화", "수"],
    "time_slots": ["오전"],
    "experiences": ["청소"],
    "capabilities": {"체력": 5, "기술": 2}
  }
}

응답:
{
  "session_id": "uuid",
  "recommendations": [
    {
      "job_id": 1,
      "title": "서울 강남 오피스 청소",
      "hourly_wage": 12000,
      "match_score": 92.5,
      "recommendation_reason": "지역 일치, 경험 일치"
    },
    ...
  ],
  "reasoning_summary": {
    "iterations": 3,
    "thoughts_count": 3,
    "actions_count": 3
  }
}
```

### 2. 음성 기반 재추천 (2차 추천)
```bash
POST /recommend/voice?session_id=<session_id>

[음성 파일 업로드 (.mp3)]

응답:
{
  "session_id": "uuid",
  "voice_text": "시급 15000원 이상 찾아줄래?",
  "recommendations": [...],
  "reasoning_summary": {...}
}
```

### 3. 세션 조회
```bash
GET /recommend/session/{session_id}

응답:
{
  "session_id": "uuid",
  "user_profile": {...},
  "recommendations": [...],
  "last_voice_intent": "시급 15000원 이상"
}
```

### 4. 추론 과정 조회 (디버깅용)
```bash
GET /recommend/session/{session_id}/reasoning

응답:
{
  "session_id": "uuid",
  "iterations": 3,
  "thoughts": [
    {
      "content": "현재 상황 분석...",
      "reasoning": "왜 이렇게 생각하는지..."
    }
  ],
  "actions": [
    {
      "tool": "rag_search",
      "params": {...}
    }
  ],
  "observations": [
    {
      "success": true,
      "data": [...],
      "analysis": "결과 분석..."
    }
  ]
}
```

### 5. 공고 이미지 업로드 (등록)
```bash
POST /post/extract

파라미터:
- file: 공고 이미지
- save_artifacts: true (CSV/SQL 저장)

응답:
{
  "status": "success",
  "job": {
    "title": "청소 일자리",
    "participants": 2,
    "hourly_wage": 12000,
    "place": "서울",
    ...
    "embedding": [0.123, 0.456, ...]
  }
}
```

## 🤖 ReAct Agent 동작 원리

### 기본 흐름
```
사용자 프로필 + 의도 입력
         ↓
    [Iteration 1]
    💭 Thought: 현재 상황 분석
    🔧 Action: Tool 선택 (예: rag_search)
    📊 Observation: 결과 평가
         ↓
    [Iteration 2]
    💭 Thought: 이전 결과가 부족하면?
    🔧 Action: 다른 Tool 선택 (예: region_specific_search)
    📊 Observation: 결과 평가
         ↓
    [충분한 결과 획득 또는 max_iterations 도달]
    ✅ 최종 답변 컴파일
         ↓
    최적의 추천 반환
```

### Tool 선택 로직
```
상황: 추천 결과 0개
→ Action: rag_search (기본 의미론적 검색 시도)

상황: 추천 결과 1-2개
→ Action: region_specific_search 또는 experience_based_search
  (다른 각도에서 추가 검색)

상황: 추천 결과 3-5개
→ Action: profile_match_filter 또는 validate_recommendations
  (결과 품질 검증 및 필터링)

상황: 추천 결과 5개 이상
→ 종료 (충분한 결과 획득)
```

## 📊 ReAct Agent vs 기존 시스템 비교

| 항목 | 기존 (Supervisor → Recommender) | ReAct Agent |
|-----|------|-----------|
| **구조** | 선형 (1회 실행) | 루프 (다중 반복) |
| **자율성** | 계획만 수립 | 자발적 의사결정 |
| **오류 복구** | Fallback만 | 자동 재시도 |
| **Tool 사용** | 1개 (RAG) | 8개 (동적 선택) |
| **결과 검증** | 없음 | 자동 검증 |
| **적응성** | 고정적 | 상황 기반 |

## 🔧 Python에서 직접 사용

### ReAct Agent 직접 사용
```python
from agents.react_agent import ReActAgent

agent = ReActAgent("data/new_work_with_embeddings.csv")

user_profile = {
    "nickname": "김할머니",
    "regions": ["서울"],
    "days": ["월", "화"],
    "time_slots": ["오전"],
    "experiences": ["청소"],
    "capabilities": {"체력": 5}
}

# 기본 추천
result = agent.run(user_profile=user_profile, intent="")

# 음성 의도 포함 추천
result = agent.run(
    user_profile=user_profile,
    intent="시급 15000원 이상"
)

print(f"추천 개수: {len(result['recommendations'])}")
print(f"반복 횟수: {result['reason']['iterations']}")
print(f"추론 과정: {result['reason']['thoughts']}")
```

### Tool Toolkit 직접 사용
```python
from agents.tools.toolkit import AgentToolkit

toolkit = AgentToolkit("data/new_work_with_embeddings.csv")

# RAG 검색
result = toolkit.rag_search(
    query="서울 청소 일자리",
    user_profile={"regions": ["서울"], "experiences": ["청소"]},
    top_k=5
)

# 지역 기반 검색
result = toolkit.region_specific_search(
    regions=["서울"],
    user_profile=user_profile,
    top_k=5
)

# 시급 필터링
result = toolkit.price_filtered_search(
    min_wage=12000,
    max_wage=20000,
    user_profile=user_profile
)

# 하이브리드 검색
result = toolkit.hybrid_search(
    query="청소 일자리",
    user_profile=user_profile
)
```

## 📈 성능 최적화

1. **Embedding 차원**: 1024 (CLOVA)
2. **검색 상위 K개**: 기본 5개
3. **Max Iterations**: 5회 (무한 루프 방지)
4. **Rate Limiting**: API 속도 제한 자동 처리
5. **결과 캐싱**: 세션 기반 (중복 검색 방지)

## 🧪 테스트

```bash
# 전체 테스트
python test_react_agent.py

# 출력:
# 🧪 Test 1: 기본 추천
# 🧪 Test 2: 음성 의도 포함 추천
# 🧪 Test 3: Tool Toolkit 동작
# 🧪 Test 4: LangGraph 통합
```

## 🎓 주요 참고 자료

- **ReAct 패턴**: https://arxiv.org/abs/2210.03629
- **LangGraph**: https://github.com/langchain-ai/langgraph
- **LangChain Agents**: https://python.langchain.com/en/latest/modules/agents.html

## 🔗 관련 컴포넌트

- Backend API: `/backend_api`
- Frontend App: `/frontend_app`
- OCR/LLM/STT: NAVER CLOVA 서비스
