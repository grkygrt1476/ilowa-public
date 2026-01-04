"""
ReAct 패턴 마이그레이션 완료

이 파일은 기존 Agent 시스템을 ReAct 패턴 기반으로 완전히 리팩토링한 내용을 정리합니다.
"""

# ============================================================
# 📋 변경사항 요약
# ============================================================

## 🆕 새로 추가된 파일

1. `agents/tools/toolkit.py` (★ 핵심)
   - AgentToolkit 클래스: 8가지 Tool 관리
   - ToolResult 클래스: 표준화된 Tool 실행 결과
   - Tool 목록:
     * rag_search: Embedding 기반 의미론적 검색
     * region_specific_search: 지역 기반 정확한 검색
     * experience_based_search: 경험 키워드 기반 검색
     * price_filtered_search: 시급 범위 필터링
     * hybrid_search: RAG + 프로필 필터링 결합
     * latest_jobs: 최신 공고
     * profile_match_filter: 프로필 기반 필터링
     * validate_recommendations: 결과 품질 검증

2. `agents/react_agent.py` (★ 핵심)
   - ReActAgent 클래스: Thought → Action → Observation 루프 구현
   - ReActThought, ReActAction, ReActObservation 클래스
   - 자율적 의사결정 및 오류 복구 로직
   - Max iterations: 5회 (무한 루프 방지)

3. `test_react_agent.py`
   - 기본 추천 테스트
   - 음성 의도 포함 추천 테스트
   - Tool Toolkit 테스트
   - LangGraph 통합 테스트

4. `README_REACT.md`
   - ReAct 패턴 상세 설명서
   - API 사용 가이드
   - 코드 예제

## 🔄 수정된 파일

1. `agents/graph_builder.py`
   - 기존: supervisor_node + recommender_node 선형 구조
   - 변경: react_node 단일 노드로 통합
   - 상태(State)에서 "plan" 제거, "reasoning" 추가

2. `main.py`
   - react_agent 인스턴스 추가
   - /recommend 엔드포인트: ReAct Agent 직접 사용
   - /recommend/voice 엔드포인트: ReAct Agent로 재실행
   - /recommend/session/{session_id}/reasoning 추가 (디버깅용)
   - 응답 형식 개선: reasoning_summary 포함

3. `requirements.txt` (추가 필요)
   - scikit-learn (toolkit의 cosine_similarity 사용)
   - langchain (기존 유지)
   - langgraph (기존 유지)

## ⛔ 레거시 코드 (여전히 존재하나 미사용)

- agents/supervisor_agent.py
- agents/recommender_agent.py

→ 호환성 유지를 위해 삭제하지 않음. 필요시 나중에 정리.

# ============================================================
# 🎯 주요 개선사항
# ============================================================

## 1. 자율성 (Autonomy)
❌ Before: 일회성 계획만 수립
✅ After: Thought → Action → Observation 루프로 자율적 재시도

## 2. 적응성 (Adaptability)
❌ Before: 고정된 Tool (RAG만)
✅ After: 8가지 Tool 동적 선택

## 3. 오류 복구 (Error Recovery)
❌ Before: 실패하면 그냥 진행
✅ After: 다른 전략 자동 시도 (max 5회)

## 4. 검증 (Validation)
❌ Before: 결과 품질 검증 없음
✅ After: 자동 품질 검증 및 종료 조건 판단

## 5. 투명성 (Transparency)
❌ Before: 추론 과정 숨겨짐
✅ After: Thought, Action, Observation 모두 기록 및 조회 가능

## 6. 확장성 (Extensibility)
❌ Before: 새 Tool 추가 어려움
✅ After: AgentToolkit에 Tool 추가하기만 하면 자동 사용

# ============================================================
# 🔧 사용 예제
# ============================================================

## 예제 1: ReAct Agent 직접 사용
```python
from agents.react_agent import ReActAgent

agent = ReActAgent("data/new_work_with_embeddings.csv")

profile = {
    "nickname": "김할머니",
    "regions": ["서울"],
    "days": ["월", "화"],
    "time_slots": ["오전"],
    "experiences": ["청소"],
    "capabilities": {"체력": 5}
}

# ReAct 루프 실행 (Thought → Action → Observation 반복)
result = agent.run(user_profile=profile, intent="")

print(f"추천: {len(result['recommendations'])}개")
print(f"반복: {result['reason']['iterations']}회")
print(f"Thoughts: {[t['content'] for t in result['reason']['thoughts']]}")
```

## 예제 2: FastAPI 엔드포인트
```bash
# 초기 추천
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_profile": {
      "nickname": "김할머니",
      "regions": ["서울"],
      ...
    }
  }'

# 음성 재추천
curl -X POST "http://localhost:8000/recommend/voice?session_id=xxx" \
  -F "audio_file=@voice.mp3"

# 추론 과정 조회
curl -X GET "http://localhost:8000/recommend/session/xxx/reasoning"
```

## 예제 3: Tool Toolkit 직접 사용
```python
from agents.tools.toolkit import AgentToolkit

toolkit = AgentToolkit("data/new_work_with_embeddings.csv")

# RAG 검색
result = toolkit.rag_search("서울 청소", user_profile={...})

# 지역 검색
result = toolkit.region_specific_search(["서울"], user_profile={...})

# 시급 필터링
result = toolkit.price_filtered_search(min_wage=12000, user_profile={...})

# 모든 Tool 확인
print(toolkit.get_available_tools())
```

# ============================================================
# 📊 ReAct 루프 상세 과정
# ============================================================

## Iteration 1: 초기 검색
```
💭 Thought: "사용자는 서울 오전 청소 일을 찾고 있다. 먼저 RAG 검색 시도."
🔧 Action: tool="rag_search", params={query="서울 청소", ...}
📊 Observation: "2개 결과 얻음 - 부족함"
   → 루프 계속
```

## Iteration 2: 지역 기반 검색
```
💭 Thought: "RAG로 부족하니 지역 기반으로 더 찾아보자"
🔧 Action: tool="region_specific_search", params={regions=["서울"], ...}
📊 Observation: "3개 추가 결과 - 총 5개"
   → 루프 계속
```

## Iteration 3: 필터링
```
💭 Thought: "5개 있지만 모두 프로필과 일치하는지 확인"
🔧 Action: tool="profile_match_filter", params={min_score=0.5, ...}
📊 Observation: "4개 통과, 평균 점수 0.75"
   → 충분함! 루프 종료
```

## Final Answer
```
✅ 최종 결과: 4개 추천
   - 반복: 3회
   - 사용 Tool: rag_search, region_specific_search, profile_match_filter
   - 평균 점수: 0.75
```

# ============================================================
# 🚀 마이그레이션 가이드
# ============================================================

## 기존 코드 → ReAct 전환

### Before (기존 방식)
```python
from agents.supervisor_agent import SupervisorAgent
from agents.recommender_agent import RecommenderAgent

supervisor = SupervisorAgent(recommender)
plan = supervisor.plan_with_llm(goal)
execution = supervisor.execute_plan(plan, goal)
```

### After (ReAct 방식)
```python
from agents.react_agent import ReActAgent

agent = ReActAgent()
result = agent.run(user_profile=profile, intent=intent)
```

## 호환성
- ✅ 기존 엔드포인트 (/recommend, /recommend/voice) 유지
- ✅ 응답 형식 호환 (recommendations 포함)
- ✅ 세션 시스템 유지
- ✅ 새로운 디버깅 엔드포인트 추가 (/recommend/session/{id}/reasoning)

# ============================================================
# 🧪 테스트 방법
# ============================================================

## 기본 테스트
```bash
python test_react_agent.py
```

결과:
```
🧪 Test 1: 기본 추천 ✅
🧪 Test 2: 음성 의도 포함 추천 ✅
🧪 Test 3: Tool Toolkit 동작 ✅
🧪 Test 4: LangGraph 통합 ✅
```

## 수동 테스트
```bash
# 서버 실행
uvicorn main:app --reload

# Swagger UI
http://localhost:8000/docs

# 수동 API 호출
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{"user_profile": {...}}'
```

## 성능 테스트 (선택적)
```python
import time
from agents.react_agent import ReActAgent

agent = ReActAgent()

# 10회 반복 측정
times = []
for i in range(10):
    start = time.time()
    agent.run(user_profile={...}, intent="")
    times.append(time.time() - start)

print(f"평균: {sum(times)/len(times):.2f}초")
print(f"최소: {min(times):.2f}초, 최대: {max(times):.2f}초")
```

# ============================================================
# 📝 다음 단계 (선택사항)
# ============================================================

1. **Tool 추가**
   - database_query: SQL 직접 쿼리
   - user_preference_history: 사용자 검색 이력 활용
   - similar_users: 유사 사용자 추천 참고

2. **LLM 기반 Tool 선택**
   - 현재: 휴리스틱 기반 (Thought 내용에서 Tool 이름 찾기)
   - 개선: LLM이 JSON으로 명시적 Tool 선택
   - 형식: {"tool": "region_specific_search", "params": {...}}

3. **메모리 시스템**
   - 사용자별 추천 이력 저장
   - 비슷한 패턴 학습
   - 피드백 기반 재정렬

4. **벡터 데이터베이스**
   - 현재: CSV 기반 (느림)
   - 개선: Weaviate, Pinecone, Milvus 등
   - 성능: O(n) → O(log n)

5. **모니터링**
   - Agent 성능 메트릭
   - Tool 선택 분포
   - 오류율 추적

# ============================================================
# 🎓 참고 자료
# ============================================================

ReAct 패턴:
https://arxiv.org/abs/2210.03629

LangChain Agents:
https://python.langchain.com/en/latest/modules/agents.html

LangGraph:
https://github.com/langchain-ai/langgraph

Agent Design Patterns:
https://lilianweng.github.io/posts/2023-06-23-agent/

# ============================================================
"""
