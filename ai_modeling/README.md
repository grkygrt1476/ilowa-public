## ilowa AI Modeling — 빠른 시작 가이드

짧고 쉽게: 서버 켜고 Swagger UI에서 몇 개만 눌러보면 전체 흐름을 이해할 수 있게 구성됐습니다.

### 1) 설치 (Windows PowerShell)
```
cd ai_modeling
pip install -r requirements.txt
```

환경 변수(.env)는 CLOVA 키가 있어야 실제 호출됩니다. 키가 없으면 일부 엔드포인트는 동작하지 않습니다.

필요한 항목 (.env 예시)
```
CLOVA_OCR_URL=...
CLOVA_OCR_SECRET=...
CLOVA_STT_URL=...
CLOVA_STT_SECRET=...
CLOVA_LLM_URL=...
CLOVA_LLM_API_KEY=...
CLOVA_EMBEDDING_HOST=...
CLOVA_EMBEDDING_API_KEY=...
AI_PROVIDER=naver  # 이후 자체 모델을 붙일 땐 local 로 전환
```

### 2) 서버 실행
```
uvicorn main:app --reload
```

브라우저에서 Swagger UI 열기: http://localhost:8000/docs

---

## Swagger UI로 바로 써보기

아래 순서대로 각각 한 번씩만 실행해보면 전체 기능을 빠르게 체험할 수 있습니다.

### A. 프로필 기반 추천 (ReAct Agent)
- 경로: POST /recommend
- Try it out → Request body에 아래 예시 붙여넣기 → Execute
```
{
  "user_profile": {
    "nickname": "홍길동",
            "regions": ["성동구", "광진구", "강남구"],
            "days": ["월요일 오전", "수요일 오전", "금요일 오전"],
            "time_slots": ["오전"],
            "experiences": ["아파트 관리", "경비/보안", "청소/미화"],
            "capabilities": {"can_lift": 10}
  }
}
```
- 기대 출력: 상위 5개 추천 리스트 + 세션 ID

### B. 음성으로 재추천
- 경로: POST /recommend/voice
- Try it out → session_id에 A 단계에서 받은 값 입력
- audio_file에 mp3 업로드(sample/test_voice.mp3 또는 사용자 음성) → Execute
- 기대 출력: 음성의도 반영된 추천 리스트

### C. 음성으로 공고 생성 (대화형)
- 경로: POST /post/create/voice
- Try it out → audio에 mp3 업로드(sample/test_voice.mp3 또는 사용자 음성) → Execute
- 기대 출력: 생성된 공고 + 부족한 항목이 있으면
  - needs_clarification=true
  - session_id / questions 포함

### D. 추가 음성으로 공고 보완 (한 번만)
- 경로: POST /post/create/voice/clarify
- Try it out → session_id에 C 단계에서 받은 값 입력
- audio에 mp3 업로드(sample/test_voice.mp3 또는 사용자 음성) → Execute
- 기대 출력: 보완된 최종 공고 (needs_clarification=false)

### E. 이미지로 공고 추출 → CSV 저장
- 경로: POST /post/extract
- Try it out → file에 이미지 업로드(sample/test_post.png) → Execute
- 기대 출력: 추출된 공고 + 저장된 CSV 행(same run)
- 참고: CSV는 `data/new_work_with_embeddings.csv`에 append, 임베딩 포함

### F. 오케스트레이션 파이프라인 (단일 진입점)
- 경로: 
  - POST `/pipeline/recommend`
  - POST `/pipeline/post/voice`
  - POST `/pipeline/post/image`
  - POST `/pipeline/post/text`
- Query `provider`를 `naver` 또는 `local`로 넘기면 즉시 다른 Provider로 전환됩니다.  
  (현재 `local`은 파인튜닝 완료 전까지 NotImplemented 오류를 반환하도록 구성했습니다.)

---

## 이 프로젝트가 하는 일 (핵심만)
- ReAct Agent: 스스로 생각(Thought)하고 도구(Action)를 선택해 관찰(Observation)하며 추천을 반복 개선합니다.
- LangGraph: 상태 그래프를 사용해 에이전트 플로우를 컴파일(프로젝트에 포함, 기본은 ReAct 단독 실행).
- Posting Agent: 음성/STT, 이미지/OCR, 텍스트 입력을 받아 제목/카테고리/설명/시급 등 구조화된 공고를 생성합니다.
- CSV RAG: 공고 데이터를 벡터로 임베딩하고, 의도/프로필과의 유사도로 추천합니다.
- Provider Layer: `AI_PROVIDER` 값으로 Naver Cloud API와 향후 파인튜닝된 오픈 모델을 손쉽게 스위칭할 수 있습니다.

---

## 폴더 구조 (요약)
```
ai_modeling/
├─ main.py                  # FastAPI 진입점, Swagger UI
├─ agents/
│  ├─ react_agent.py        # ReAct 추천 에이전트 (메인)
│  ├─ posting_agent.py      # 음성/이미지/텍스트 → 공고 추출
│  ├─ graph_builder.py      # LangGraph 상태 그래프 정의
│  └─ tools/
│     ├─ toolkit.py         # 검색/필터 도구 모음(8종)
│     └─ csv_rag_tool.py    # CSV RAG 검색 엔진
├─ routers/
│  ├─ post_create.py        # 음성/이미지/텍스트 공고 생성 API
│  ├─ post_automation.py    # OCR→LLM→CSV 저장 API
│  └─ post_approval.py      # 승인 플로우 API
├─ orchestration/
│  └─ pipeline.py           # Provider 기반 전체 파이프라인 오케스트레이터
├─ services/                # CLOVA OCR/STT/LLM/Embedding, HTML 파서
├─ data/                    # new_work_with_embeddings.csv 등
└─ schemas/, utils/         # Pydantic 모델, CSV/SQL 저장 유틸
```

---

## 빠른 문제 해결
- 401 Unauthorized: .env의 CLOVA 키 확인
- Embedding 차원 오류: `ai_modeling/rebuild_embeddings.py` 실행해 CSV 임베딩 재생성
- Swagger 업로드 실패: 파일 확장자/용량 확인 (mp3, png/jpg 권장)

## Public repo policy (samples)
- 공개 repo에는 실제 음성/주소/전화번호/URL 등 실데이터를 포함하지 않습니다.
- `sample/test_voice.mp3`는 데모용 샘플이며 실제 STT 테스트는 사용자 음성 업로드를 권장합니다.

---

Swagger UI로 순서대로 A→E 실행해보시면 전체 흐름 이해 가능할듯 합니다!

---

## 공고 승인 엔드포인트 (간단 목록)
- POST `/post/approval/submit` — 공고 승인 요청 등록
- GET `/post/approval/pending` — 대기 중인 공고 목록 조회
- GET `/post/approval/{pending_id}` — 특정 대기 공고 상세
- POST `/post/approval/{pending_id}/approve` — 승인 처리(→ CSV 반영)
- DELETE `/post/approval/{pending_id}/reject` — 반려 처리
---


## 세션 흐름 (텍스트 다이어그램)
```
# 추천 흐름
/recommend  ──▶ (returns session_id)
                 │
                 └──▶ /recommend/voice (same session_id, mp3)

# 공고 생성 흐름 (대화형)
/post/create/voice  ──▶ (needs_clarification? true → returns session_id, questions)
                           │
                           └──▶ /post/create/voice/clarify (same session_id, mp3) ──▶ done

# 비고: 세션은 메모리 저장이므로 서버 재시작 시 초기화됩니다.
```
---

## 세션 흐름 다이어그램
```
추천 흐름:
/recommend (session_id 생성) → /recommend/voice (같은 session_id로 재추천)

공고 생성 흐름:
/post/create/voice (필요 시 session_id 생성) → /post/create/voice/clarify (한 번만, 완료)

이미지 흐름:
/post/extract (독립 실행, CSV 직접 저장)
```

## Response Body 구조 확인 방법
**Swagger UI 활용**: 
- `/docs` → 각 엔드포인트 클릭 → Try it out → Execute → Response body JSON 구조 즉시 확인
- 실제 Response 예시를 복사해서 백엔드/프론트 타입 정의에 활용 가능

---
