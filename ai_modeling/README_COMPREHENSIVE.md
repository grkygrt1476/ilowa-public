# 🤖 AI 기반 지능형 일자리 추천 시스템 (ilowa AI Modeling)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Enabled-orange.svg)](https://github.com/langchain-ai/langgraph)
[![CLOVA AI](https://img.shields.io/badge/CLOVA-AI-brightgreen.svg)](https://www.ncloud.com/)

## 📋 목차

1. [프로젝트 개요](#-프로젝트-개요)
2. [핵심 기능](#-핵심-기능)
3. [시스템 아키텍처](#-시스템-아키텍처)
4. [Agent 구조 상세](#-agent-구조-상세)
5. [LangGraph 기반 Agent 시스템](#-langgraph-기반-agent-시스템)
6. [프로젝트 구조](#-프로젝트-구조)
7. [주요 컴포넌트 설명](#-주요-컴포넌트-설명)
8. [API 엔드포인트](#-api-엔드포인트)
9. [설치 및 실행](#-설치-및-실행)
10. [사용 예시](#-사용-예시)
11. [기술 스택](#-기술-스택)
12. [문제 해결 가이드](#-문제-해결-가이드)

---

## 🎯 프로젝트 개요

**ilowa AI Modeling**은 시니어 대상 맞춤형 소일거리 추천 및 공고 자동 생성 시스템입니다.

### 핵심 특징

- ✅ **진정한 Agent 기반 시스템**: ReAct (Reasoning + Acting) 패턴 구현
- ✅ **LangGraph 통합**: 상태 관리 및 워크플로우 자동화
- ✅ **멀티모달 입력 처리**: 음성(STT), 이미지(OCR), 텍스트 지원
- ✅ **지능형 추천 엔진**: RAG + Profile Matching + Diversity Control
- ✅ **대화형 공고 작성**: 음성 기반 대화형 필드 완성
- ✅ **자동화된 데이터 추출**: 표/텍스트 하이브리드 파싱

---

## 🌟 핵심 기능

### 1. 지능형 일자리 추천 (ReAct Agent)

**Thought → Action → Observation** 루프를 통한 자율적 추천:

```
사용자 프로필 입력
    ↓
[THOUGHT] 현재 상황 분석 → 전략 수립
    ↓
[ACTION] 도구 선택 및 실행 (8가지 도구 중 선택)
    ↓
[OBSERVATION] 결과 평가 → 충분? or 재시도?
    ↓
(반복, 최대 8회)
    ↓
최종 추천 결과 (다양성 보장: 같은 제목 최대 1개)
```

**지원 도구 (Tools):**
1. `rag_search`: 의미론적 유사도 검색
2. `region_specific_search`: 지역 기반 정확 검색
3. `experience_based_search`: 경험 키워드 매칭
4. `price_filtered_search`: 시급 범위 필터링
5. `hybrid_search`: RAG + 프로필 결합
6. `latest_jobs`: 최신 공고
7. `profile_match_filter`: 프로필 일치도 필터링
8. `validate_recommendations`: 추천 품질 검증

### 2. 대화형 공고 생성 (PostingAutomationAgent)

**음성 → 구조화된 공고**:

```
음성 녹음 "산책 도와줄 사람이 필요해요"
    ↓
STT (CLOVA Speech-to-Text)
    ↓
LLM 추출 (자동 생성, 복사 없음):
  - 제목: "반려동물 산책 도우미"
  - 카테고리: "반려동물 돌봄"
  - 설명: "반려동물 산책을 도와주실 분을 모집합니다..."
  - 자격 요건: "반려동물 양육 경험자 우대"
    ↓
빠진 필드 감지 → 질문 생성
    ↓
추가 음성 입력 → 병합 → 완료
```

**이미지 → 구조화된 공고**:

```
공고 이미지 업로드 (표/텍스트 혼재)
    ↓
OCR (CLOVA Optical Character Recognition)
    ↓
표 자동 인식 → Key-Value 추출:
  "사업명": "청소 도우미"
  "모집인원": "2명"
  "임금수준(월)": "761,040원"
  "근무시간": "주 5회, 일 3시간"
    ↓
자동 매핑 + LLM 보완:
  - 시급 자동 계산: 761,040 ÷ (5일 × 3시간 × 4.345주) = 11,684원
  - 지역 추출: "송파시니어클럽" → "서울특별시 송파구"
  - 자연어 설명 생성
    ↓
CSV + Embedding 저장
```

### 3. 음성 기반 재추천

```
초기 추천 결과 → "더 가까운 곳으로 보여줘" (음성)
    ↓
STT → "더 가까운 곳"
    ↓
ReAct Agent 재실행:
  [THOUGHT] 이전 추천이 지역 우선순위가 낮았음
  [ACTION] region_specific_search 사용
  [OBSERVATION] 거리 기준 재정렬
    ↓
업데이트된 추천 결과
```

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│                  (main.py + 3 Routers)                       │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──────────────────┬──────────────────┬───────────
             │                  │                  │
             ▼                  ▼                  ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │   ReAct      │   │  Posting     │   │  Approval    │
    │   Agent      │   │  Automation  │   │  Workflow    │
    │              │   │  Agent       │   │              │
    └──────┬───────┘   └──────┬───────┘   └──────────────┘
           │                  │
           │                  │
    ┌──────▼───────┐   ┌──────▼───────┐
    │   Toolkit    │   │   CLOVA      │
    │   (8 Tools)  │   │   Services   │
    │              │   │   (4 APIs)   │
    └──────┬───────┘   └──────┬───────┘
           │                  │
           ▼                  ▼
    ┌────────────────────────────────┐
    │      CSVRAGTool + Embedding    │
    │   (new_work_with_embeddings)   │
    └────────────────────────────────┘
```

### LangGraph 통합 워크플로우

```
┌─────────────────────────────────────────────┐
│           LangGraph StateGraph              │
│                                             │
│   ┌─────────────────────────────────────┐  │
│   │  AgentState (TypedDict)             │  │
│   │  - user_profile                     │  │
│   │  - intent                           │  │
│   │  - recommendations                  │  │
│   │  - reasoning                        │  │
│   └─────────────────────────────────────┘  │
│              │                              │
│              ▼                              │
│   ┌─────────────────────────────────────┐  │
│   │      react_node                     │  │
│   │   (ReAct Agent 실행)                │  │
│   │   Thought → Action → Observation    │  │
│   └─────────────────────────────────────┘  │
│              │                              │
│              ▼                              │
│            END                              │
└─────────────────────────────────────────────┘
```

---

## 🤖 Agent 구조 상세

### 1️⃣ ReAct Agent (Agent)

**위치**: `agents/react_agent.py`

**핵심 개념**: Agent는 단순히 LLM을 호출하는 것이 아니라, **자율적으로 생각하고 행동하며 결과를 평가**합니다.

#### ReAct 루프 동작 원리

```python
# 의사 코드
for iteration in range(max_iterations=8):
    # 1️⃣ THOUGHT: 현재 상황 분석
    thought = agent._think(profile, intent, current_results, history)
    # "결과가 2개뿐이고 모두 강남구... 다른 지역도 찾아봐야겠다"
    
    # 2️⃣ ACTION: 도구 선택 및 실행
    action = agent._choose_action(thought)
    # "region_specific_search를 송파구로 실행"
    
    tool_result = toolkit.execute_tool(action.tool, **action.params)
    
    # 3️⃣ OBSERVATION: 결과 평가
    observation = agent._analyze_observation(tool_result)
    # "5개 결과 획득, 평균 점수 0.82 → 충분함"
    
    if should_stop(observation):
        break  # 충분한 결과 확보
```

#### Diversity Control (다양성 보장)

```python
# 같은 제목이 반복되는 것을 방지
# 예: "청소 도우미", "청소도우미", "청소 보조" → 모두 "청소도우미"로 정규화
normalized_title = title.lower().strip().replace(" ", "")

# 정규화된 제목별로 최대 1개만 선택
title_counts = {}
for job in sorted_jobs:
    norm = normalize_title(job['title'])
    if title_counts.get(norm, 0) < 1:  # 최대 1개
        selected.append(job)
        title_counts[norm] = title_counts.get(norm, 0) + 1
```

### 2️⃣ PostingAutomationAgent

**위치**: `agents/posting_agent.py`

**역할**: 음성/이미지/텍스트를 구조화된 `JobPost` 객체로 변환

#### 주요 함수

**1. `extract_from_voice(file_path)`**
- STT → 텍스트 → `extract_from_text`
- 자격 요건 자동 추출 (키워드 기반)

**2. `extract_from_image_bytes(image_bytes)`**
- OCR → HTML → 표 추출 → Key-Value 매핑
- LLM으로 추가 보완
- 지역 자동 추출 (정규식 패턴)

**3. `extract_from_text(text)`**
- LLM 프롬프트로 구조화
- Fallback: 정규식 기반 추출

**4. `check_missing_fields(post)`**
- 필수 필드 누락 확인
- 질문 자동 생성

**5. `merge_additional_input(post, additional_text)`**
- 추가 음성 입력 병합
- 자연어 설명 재생성

#### 자동 계산 및 생성 기능

```python
# 시급 자동 계산
hourly_wage = monthly_wage / (days_per_week * hours_per_day * 4.345)

# 지역 자동 추출
"송파시니어클럽" → "서울특별시 송파구"
"부산시 해운대구" → "부산시 해운대구"

# 자격 요건 자동 생성
"반려동물" in voice_text → "반려동물 양육 경험자 우대"
"아이", "육아" in voice_text → "육아 경험자 우대"
```

### 3️⃣ Toolkit (도구 레지스트리)

**위치**: `agents/tools/toolkit.py`

**역할**: ReAct Agent가 사용하는 8가지 도구 관리

```python
class AgentToolkit:
    def __init__(self):
        self.tools = {
            "rag_search": self.rag_search,
            "region_specific_search": self.region_specific_search,
            # ... 6 more tools
        }
    
    def execute_tool(self, tool_name, **kwargs):
        return self.tools[tool_name](**kwargs)
```

### 4️⃣ CSVRAGTool (검색 엔진)

**위치**: `agents/tools/csv_rag_tool.py`

**역할**: Embedding 기반 유사도 검색

```python
# 1. Query를 Embedding으로 변환
query_embedding = get_clova_embedding(query)

# 2. CSV의 모든 공고 Embedding과 Cosine Similarity 계산
similarities = cosine_similarity([query_embedding], job_embeddings)

# 3. 상위 K개 반환
top_k_jobs = sorted_by_similarity[:k]
```

---

## 🔗 LangGraph 기반 Agent 시스템

### LangGraph란?

[LangGraph](https://github.com/langchain-ai/langgraph)는 LangChain 팀에서 개발한 **상태 기반 워크플로우 프레임워크**입니다.

### 이 프로젝트는 Agent 기반 시스템인가?

**✅ 네, 진정한 Agent 기반 시스템입니다.**

#### Agent의 정의와 이 시스템의 구현

| Agent 요소 | 이 시스템의 구현 |
|-----------|----------------|
| **Autonomy (자율성)** | ReAct Agent가 스스로 도구를 선택하고 실행 순서 결정 |
| **Reactivity (반응성)** | Observation 결과에 따라 전략 변경 (예: 결과 부족 → 다른 도구 시도) |
| **Goal-Directedness** | 사용자 프로필과 intent에 맞는 최적의 추천 생성 목표 |
| **Learning** | 이전 시도 결과를 분석하여 다음 행동 결정 |
| **State Management** | LangGraph의 `AgentState`로 상태 추적 |

#### LangGraph 사용 여부

**✅ 네, LangGraph를 사용합니다.**

**증거**:
```python
# agents/graph_builder.py
from langgraph.graph import StateGraph, END

def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("react_agent", react_node)
    workflow.set_entry_point("react_agent")
    workflow.add_edge("react_agent", END)
    return workflow.compile()

# main.py
from agents.graph_builder import build_graph
graph = build_graph()  # LangGraph 컴파일
```

**하지만 현재는 선택적 사용**:
- 기본적으로 `ReActAgent`를 직접 호출 (`main.py`의 `/recommend` 엔드포인트)
- LangGraph는 확장성을 위해 준비된 인프라 (복잡한 멀티 Agent 시나리오 대비)

#### Agent인가?

**✅ 네, Agent입니다.**

Agent의 핵심은 **자율적 의사결정**
**이 시스템의 Agent 특성**:
1. **ReAct 패턴**: Thought → Action → Observation 루프
2. **Tool Selection**: 8가지 도구 중 상황에 맞게 선택
3. **Iterative Refinement**: 결과 평가 후 재시도
4. **Context Awareness**: 이전 시도 결과 기억

**LangGraph의 역할**:
- 상태 관리 편의성 제공
- 복잡한 워크플로우 시각화
- 멀티 Agent 협업 지원 (확장 가능)

### Supervisor Agent와 Recommender Agent

**위치**: `agents/supervisor_agent.py`, `agents/recommender_agent.py`

**현재 상태**: 레거시 코드 (ReAct Agent로 대체됨)

**역할**:
- `SupervisorAgent`: LLM 기반 계획 수립 (Plan-and-Execute 패턴)
- `RecommenderAgent`: CSV RAG 검색 래퍼

**사용 여부**: ❌ 현재 미사용 (ReAct Agent가 더 강력함)

---

## 📁 프로젝트 구조

```
ai_modeling/
├── 📄 main.py                    # FastAPI 애플리케이션 (메인 진입점)
├── 📄 requirements.txt           # Python 패키지 의존성
├── 📄 .env                       # 환경 변수 (CLOVA API Keys)
│
├── 📁 agents/                    # Agent 구현
│   ├── 📄 react_agent.py        # ✅ 핵심 ReAct Agent
│   ├── 📄 posting_agent.py      # ✅ 공고 자동 생성 Agent
│   ├── 📄 graph_builder.py      # ✅ LangGraph 워크플로우
│   ├── 📄 recommender_agent.py  # ⚠️ 레거시 (ReAct로 대체)
│   ├── 📄 supervisor_agent.py   # ⚠️ 레거시 (ReAct로 대체)
│   └── 📁 tools/
│       ├── 📄 toolkit.py        # ✅ 8가지 도구 레지스트리
│       └── 📄 csv_rag_tool.py   # ✅ RAG 검색 엔진
│
├── 📁 routers/                   # FastAPI 라우터
│   ├── 📄 post_automation.py    # ✅ 이미지 OCR → CSV 저장
│   ├── 📄 post_create.py        # ✅ 음성 대화형 공고 생성
│   └── 📄 post_approval.py      # ✅ 공고 승인/반려 워크플로우
│
├── 📁 services/                  # 외부 서비스 래퍼
│   ├── 📄 clova_ocr.py          # ✅ CLOVA OCR API
│   ├── 📄 clova_stt.py          # ✅ CLOVA STT API
│   ├── 📄 clova_llm.py          # ✅ CLOVA LLM API
│   ├── 📄 clova_embedding.py    # ✅ CLOVA Embedding API
│   └── 📄 html_parser.py        # ✅ OCR HTML → 구조화 데이터
│
├── 📁 schemas/                   # Pydantic 스키마
│   ├── 📄 job_post_schema.py    # ✅ JobPost, JobPostResponse
│   └── 📄 post_automation_schema.py
│
├── 📁 models/                    # 데이터 모델
│   └── 📄 job_model.py
│
├── 📁 utils/                     # 유틸리티
│   └── 📄 db.py                 # ✅ CSV/SQL 저장 함수
│
├── 📁 data/                      # 데이터 파일
│   ├── 📄 new_work_with_embeddings.csv  # ✅ 공고 데이터 + Embedding
│   ├── 📄 insert_job.sql
│   └── 📄 jobs_upload.csv
│
├── 📁 sample/                    # 테스트 샘플
│   ├── 📄 test_post.png
│   └── 📄 test_voice.mp3
│
└── 📁 __pycache__/               # Python 캐시
```

### ✅ 사용 중인 파일 vs ⚠️ 레거시 파일

#### ✅ 사용 중인 핵심 파일

**Agent 구현**:
- `agents/react_agent.py` - 메인 추천 Agent
- `agents/posting_agent.py` - 공고 생성 Agent
- `agents/graph_builder.py` - LangGraph 통합
- `agents/tools/toolkit.py` - 도구 레지스트리
- `agents/tools/csv_rag_tool.py` - RAG 검색 엔진

**API 라우터**:
- `routers/post_automation.py` - 이미지 OCR 처리
- `routers/post_create.py` - 음성 대화형 공고
- `routers/post_approval.py` - 승인 워크플로우

**서비스**:
- `services/clova_*.py` - 4개 CLOVA API 래퍼
- `services/html_parser.py` - 표 파싱

**스키마/모델**:
- `schemas/job_post_schema.py` - 공고 데이터 구조

#### ⚠️ 레거시 파일 (현재 미사용)

- `agents/recommender_agent.py` - ReAct Agent로 대체됨
- `agents/supervisor_agent.py` - ReAct Agent로 대체됨

**이유**: ReAct Agent가 Supervisor + Recommender의 기능을 통합하고 더 강력한 자율성 제공

---

## 🔧 주요 컴포넌트 설명

### 1. CLOVA AI Services

Naver Cloud Platform의 AI 서비스들:

#### 1-1. CLOVA OCR (Optical Character Recognition)

```python
# services/clova_ocr.py
def run_clova_ocr(image_bytes: bytes) -> str:
    """이미지 → HTML 형태의 텍스트"""
    # 표, 텍스트 블록, 좌표 정보 포함
```

**활용**:
- 공고 이미지에서 표 데이터 추출
- 좌표 정보로 레이아웃 분석

#### 1-2. CLOVA STT (Speech-To-Text)

```python
# services/clova_stt.py
def clova_stt_from_file(file_path: str, lang: str) -> dict:
    """음성 파일 → 텍스트"""
    # {"text": "산책 도와줄 사람이 필요해요"}
```

**활용**:
- 음성 기반 공고 생성
- 음성 기반 재추천

#### 1-3. CLOVA LLM (Language Model)

```python
# services/clova_llm.py
class CompletionExecutor:
    def execute(self, request_data: dict) -> str:
        """LLM 완성 요청"""
```

**활용**:
- 텍스트 → 구조화된 JSON
- 자연어 설명 생성
- ReAct Thought 생성

#### 1-4. CLOVA Embedding

```python
# services/clova_embedding.py
def get_clova_embedding(text: str) -> List[float]:
    """텍스트 → 벡터 (1024차원)"""
```

**활용**:
- RAG 검색용 Query Embedding
- 공고 데이터 Embedding

### 2. CSV RAG (Retrieval-Augmented Generation)

```python
# agents/tools/csv_rag_tool.py
class CSVRAGTool:
    def query(self, query: str, top_k: int) -> List[Dict]:
        query_emb = get_clova_embedding(query)
        similarities = cosine_similarity([query_emb], self.embeddings)
        return top_k_results
```

**데이터 구조**:
```csv
job_id,title,participants,hourly_wage,place,address,work_days,start_time,end_time,client,description,embedding
1,"청소 도우미",2,12000,"서울","강남구 역삼동","1111100","09:00:00","18:00:00","강남시니어클럽","청소 업무...",[-0.123,0.456,...]
```

### 3. 대화형 워크플로우 (Conversational Flow)

```python
# routers/post_create.py
voice_sessions = {}  # 세션 저장소

@router.post("/create/voice")
async def create_post_from_voice(audio: UploadFile):
    post = agent.extract_from_voice(audio_path)
    missing = agent.check_missing_fields(post)
    
    if missing["needs_clarification"]:
        session_id = str(uuid.uuid4())
        voice_sessions[session_id] = {"post": post, "missing": missing}
        return {
            "session_id": session_id,
            "needs_clarification": True,
            "questions": missing["questions"]
        }
    
    return {"success": True, "post": post}

@router.post("/create/voice/clarify")
async def clarify_post(session_id: str, audio: UploadFile):
    session = voice_sessions[session_id]
    additional_text = stt_from_file(audio_path)
    merged_post = agent.merge_additional_input(session["post"], additional_text)
    del voice_sessions[session_id]  # 세션 종료
    return {"success": True, "post": merged_post}
```

---

## 🌐 API 엔드포인트

### 추천 API

#### 1️⃣ POST `/recommend`

**초기 추천** (프로필 기반)

**Request**:
```json
{
  "user_profile": {
    "nickname": "홍길동",
    "regions": ["서울 강남구", "서울 송파구"],
    "days": ["월요일", "수요일", "금요일"],
    "time_slots": ["오전", "오후"],
    "experiences": ["청소", "정리"],
    "capabilities": {"can_lift": 10}
  }
}
```

**Response**:
```json
{
  "session_id": "uuid-1234",
  "user_profile": {...},
  "recommendations": [
    {
      "job_id": 123,
      "title": "청소 도우미",
      "hourly_wage": 12000,
      "place": "서울",
      "address": "강남구 역삼동",
      "match_score": 85.5,
      "recommendation_reason": "지역 일치, 경험 일치"
    },
    // ... 최대 5개
  ],
  "reasoning_summary": {
    "iterations": 3,
    "thoughts_count": 3,
    "actions_count": 3
  }
}
```

#### 2️⃣ POST `/recommend/voice`

**음성 기반 재추천**

**Parameters**:
- `session_id`: 초기 추천의 세션 ID
- `audio_file`: 음성 파일 (MP3)

**Response**:
```json
{
  "session_id": "uuid-1234",
  "voice_text": "더 가까운 곳으로 보여줘",
  "recommendations": [...],
  "message": "✅ 음성 기반 재추천 완료"
}
```

#### 3️⃣ GET `/recommend/session/{session_id}`

**세션 조회**

#### 4️⃣ GET `/recommend/session/{session_id}/reasoning`

**추론 과정 상세 조회** (디버깅용)

---

### 공고 생성 API

#### 1️⃣ POST `/post/create/voice`

**음성 기반 공고 생성 (대화형)**

**Parameters**:
- `audio`: 음성 파일 (MP3/WAV)

**Response (빈 필드 있는 경우)**:
```json
{
  "success": true,
  "post": {
    "title": "산책 도우미",
    "category": "반려동물 돌봄",
    "description": "반려동물 산책을 도와주실 분...",
    "region": "",  // 빈 필드
    "schedule_days": [],  // 빈 필드
    "hourly_wage": 0  // 빈 필드
  },
  "session_id": "uuid-5678",
  "needs_clarification": true,
  "questions": [
    "어느 지역에서 근무하실 예정인가요?",
    "근무 가능한 요일을 알려주세요.",
    "희망 시급을 알려주세요."
  ]
}
```

**Response (완료)**:
```json
{
  "success": true,
  "post": {...},  // 모든 필드 채워짐
  "needs_clarification": false
}
```

#### 2️⃣ POST `/post/create/voice/clarify`

**추가 음성 입력 (한 번만)**

**Parameters**:
- `session_id`: 세션 ID
- `audio`: 추가 음성 파일

**Response**:
```json
{
  "success": true,
  "post": {...},  // 병합된 결과
  "needs_clarification": false,
  "message": "공고 생성 완료. 필요시 직접 편집하실 수 있습니다."
}
```

#### 3️⃣ POST `/post/create/image`

**이미지 기반 공고 생성**

**Parameters**:
- `image`: 이미지 파일 (PNG/JPG)

#### 4️⃣ POST `/post/create/text`

**텍스트 기반 공고 생성**

**Request Body**:
```json
{
  "text": "청소 도우미 모집합니다. 시급 12000원..."
}
```

---

### 공고 관리 API

#### 1️⃣ POST `/post/extract`

**이미지 업로드 → OCR → CSV 저장**

**Parameters**:
- `file`: 이미지 파일
- `save_artifacts`: 저장 여부 (기본 true)

**Response**:
```json
{
  "status": "success",
  "post": {...},
  "saved_row": {
    "job_id": 456,
    "title": "청소 도우미",
    "embedding": [-0.123, 0.456, ...]
  }
}
```

#### 2️⃣ POST `/post/approval/submit`

**공고 승인 요청**

#### 3️⃣ GET `/post/approval/pending`

**대기 중인 공고 목록**

#### 4️⃣ POST `/post/approval/{pending_id}/approve`

**공고 승인 → CSV 추가**

#### 5️⃣ DELETE `/post/approval/{pending_id}/reject`

**공고 반려**

---

## 🚀 설치 및 실행

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/grkygrt1476/ilowa.git
cd ilowa/ai_modeling

# 가상환경 생성 (선택)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```env
# CLOVA OCR
CLOVA_OCR_URL=https://naveropenapi.apigw.ntruss.com/...
CLOVA_OCR_SECRET=your_ocr_secret_key

# CLOVA STT
CLOVA_STT_URL=https://naveropenapi.apigw.ntruss.com/...
CLOVA_STT_SECRET=your_stt_secret_key

# CLOVA LLM (Naver Cloud LLM)
CLOVA_LLM_URL=https://clovastudio.apigw.ntruss.com/...
CLOVA_LLM_API_KEY=your_llm_api_key

# CLOVA Embedding
CLOVA_EMBEDDING_HOST=clovastudio.apigw.ntruss.com
CLOVA_EMBEDDING_API_KEY=your_embedding_api_key
CLOVA_EMBEDDING_REQUEST_ID=your_request_id

# Service
PORT=8000
```

### 3. 서버 실행

```bash
# 개발 모드 (자동 리로드)
uvicorn main:app --reload --port 8000

# 프로덕션 모드
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Swagger UI 접속

```
http://localhost:8000/docs
```

---

## 📖 사용 예시

### 예시 1: 초기 추천

```bash
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_profile": {
      "nickname": "홍길동",
      "regions": ["서울 강남구"],
      "days": ["월요일", "수요일"],
      "time_slots": ["오전"],
      "experiences": ["청소"],
      "capabilities": {}
    }
  }'
```

### 예시 2: 음성 재추천

```bash
curl -X POST "http://localhost:8000/recommend/voice?session_id=uuid-1234" \
  -F "audio_file=@voice.mp3"
```

### 예시 3: 음성 공고 생성

```bash
# 1단계: 초기 음성 입력
curl -X POST "http://localhost:8000/post/create/voice" \
  -F "audio=@voice1.mp3"

# 응답: needs_clarification=true, session_id, questions

# 2단계: 추가 음성 입력
curl -X POST "http://localhost:8000/post/create/voice/clarify?session_id=uuid-5678" \
  -F "audio=@voice2.mp3"

# 응답: 완성된 공고
```

### 예시 4: 이미지 공고 추출

```bash
curl -X POST "http://localhost:8000/post/extract" \
  -F "file=@job_poster.png"
```

---

## 🛠️ 기술 스택

### 백엔드 프레임워크
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증 및 스키마

### AI/ML
- **LangGraph**: Agent 워크플로우 관리
- **LangChain**: LLM 통합 (간접 사용)
- **CLOVA AI**: OCR, STT, LLM, Embedding
- **scikit-learn**: Cosine Similarity 계산
- **NumPy/Pandas**: 데이터 처리

### 데이터
- **CSV**: 공고 데이터 저장
- **JSON**: Embedding 저장 형식

### 기타
- **BeautifulSoup4**: HTML 파싱
- **python-dotenv**: 환경 변수 관리
- **Requests**: HTTP 클라이언트

---

## 🐛 문제 해결 가이드

### 1. LangGraph Import 오류

**증상**:
```python
ImportError: cannot import name 'StateGraph' from 'langgraph.graph'
```

**해결**:
```bash
pip install --upgrade langgraph
```

### 2. CLOVA API 인증 오류

**증상**:
```
401 Unauthorized
```

**해결**:
- `.env` 파일의 API Key 확인
- Naver Cloud Console에서 서비스 활성화 확인
- 월 사용량 한도 확인

### 3. Embedding 차원 불일치

**증상**:
```
ValueError: Embedding dimension mismatch
```

**해결**:
```bash
# CSV 재생성
python rebuild_embeddings.py
```

### 4. 음성 인식 실패

**증상**:
```json
{"success": false, "message": "음성 인식 실패"}
```

**해결**:
- 음성 파일 형식 확인 (MP3 권장)
- 파일 크기 확인 (10MB 이하)
- 언어 설정 확인 (`lang="Kor"`)

### 5. ReAct Agent가 루프를 종료하지 않음

**증상**: 8번 반복 후에도 결과 부족

**해결**:
```python
# agents/react_agent.py
# max_iterations 증가 또는 종료 조건 완화
self.max_iterations = 10  # 기본 8
```
