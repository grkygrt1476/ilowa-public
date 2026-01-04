"""
ReAct Agent: Thought -> Action -> Observation Loop

Agent가 자율적으로 도구를 선택하고 실행하며,
피드백을 받아 재시도 또는 다른 전략을 시도하는 진정한 Agent 구현
"""
import json
import math
import re
from typing import Any, Dict, List, Optional

from ai_modeling.agents.tools.toolkit import AgentToolkit, ToolResult
from ai_modeling.services.providers import AIProvider, get_ai_provider
from ai_modeling.utils.rag_paths import resolve_rag_csv_path


class ReActThought:
    """Agent의 생각(Thought) 표현"""
    def __init__(self, content: str, reasoning: str = ""):
        self.content = content
        self.reasoning = reasoning
    
    def to_dict(self):
        return {
            "content": self.content,
            "reasoning": self.reasoning
        }


class ReActAction:
    """Agent의 행동(Action) 표현"""
    def __init__(self, tool: str, params: Dict[str, Any]):
        self.tool = tool
        self.params = params
    
    def to_dict(self):
        return {
            "tool": self.tool,
            "params": self.params
        }


class ReActObservation:
    """Agent의 관찰(Observation) 표현"""
    def __init__(self, tool_result: ToolResult, analysis: str = ""):
        self.success = tool_result.success
        self.data = tool_result.data
        self.message = tool_result.message
        self.analysis = analysis
    
    def to_dict(self):
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "analysis": self.analysis
        }


class ReActAgent:
    """
    진정한 Agent: Thought -> Action -> Observation 루프
    
    사용자 프로필 기반 일자리 추천을 위해 자율적으로:
    1. 상황을 분석 (Thought)
    2. 어떤 Tool을 사용할지 결정 (Action)
    3. 결과를 평가 (Observation)
    4. 충분하면 종료, 아니면 다시 반복
    """
    
    def __init__(
        self,
        csv_path: Optional[str] = None,
        max_per_title: int = 2,
        desired_k: int = 5,
        provider: Optional[AIProvider] = None,
    ):
        self.provider = provider or get_ai_provider()
        self.provider_name = getattr(self.provider, "name", "unknown")
        self.csv_path = csv_path or str(resolve_rag_csv_path())
        self.toolkit = AgentToolkit(self.csv_path, provider=self.provider)
        self.max_iterations = 8  # diversity를 위해 더 많은 시도 허용
        self.iteration_count = 0
        # diversity settings (configurable)
        # 최대 같은 title 허용 개수 (기본 2)
        self.max_per_title = max_per_title
        # 최종 추천 수
        self.desired_k = desired_k
        
        # 추론 과정 기록
        self.thoughts: List[ReActThought] = []
        self.actions: List[ReActAction] = []
        self.observations: List[ReActObservation] = []
    
    def run(self, user_profile: Dict[str, Any], intent: str = "", previous_recommendations: List[Dict] = None) -> Dict[str, Any]:
        """
        Agent 실행: ReAct 루프
        
        Args:
            user_profile: 사용자 정보 (지역, 경험, 선호도 등)
            intent: 사용자 의도 (음성 또는 추가 요청)
            previous_recommendations: 이전 추천 결과 (재추천 시 사용)
        
        Returns:
            최종 추천 결과
        """
        if previous_recommendations is None:
            previous_recommendations = []
        print(f"\n{'='*60}")
        print(f"🤖 ReAct Agent 시작")
        print(f"{'='*60}")
        
        self.iteration_count = 0
        self.thoughts = []
        self.actions = []
        self.observations = []
        
        final_recommendations = []
        
        # ReAct 루프 시작
        for iteration in range(self.max_iterations):
            self.iteration_count = iteration + 1
            print(f"\n[Iteration {self.iteration_count}/{self.max_iterations}]")
            
            # =========== 1️⃣ THOUGHT: 현재 상황 분석 ===========
            thought = self._think(user_profile, intent, final_recommendations, self.observations, previous_recommendations)
            self.thoughts.append(thought)
            
            print(f"💭 Thought: {thought.content}")
            if thought.reasoning:
                print(f"   Reasoning: {thought.reasoning}")
            
            # =========== 종료 조건 확인 ===========
            if self._should_stop(thought, final_recommendations):
                print(f"✅ 충분한 결과 얻음 - 루프 종료")
                break
            
            # =========== 2️⃣ ACTION: Tool 선택 및 실행 ===========
            action = self._choose_and_execute_action(thought, user_profile, intent)
            self.actions.append(action)
            
            print(f"🔧 Action: {action.tool}")
            print(f"   Params: {json.dumps(action.params, ensure_ascii=False, indent=2)}")
            
            # =========== 3️⃣ OBSERVATION: 결과 평가 ===========
            # Tool 실행 및 결과 기록
            tool_result = self.toolkit.execute_tool(action.tool, **action.params)
            
            # 결과 분석
            observation = self._analyze_observation(
                tool_result,
                user_profile,
                final_recommendations
            )
            self.observations.append(observation)
            
            print(f"📊 Observation: {observation.analysis}")
            print(f"   Result count: {len(observation.data) if isinstance(observation.data, list) else 'N/A'}")
            
            # 성공한 경우 최종 결과에 추가
            if observation.success and isinstance(observation.data, list):
                final_recommendations = self._merge_recommendations(
                    final_recommendations,
                    observation.data
                )
                print(f"   누적 결과: {len(final_recommendations)}개")
        
        # 루프 종료 후: 만약 추천이 하나도 없다면 안전한 대체(fallback)로 최신 공고를 가져와 채웁니다.
        if not final_recommendations:
            try:
                print("[FALLBACK] 루프 종료 후 추천 없음 -> latest_jobs로 대체 시도")
                latest_res = self.toolkit.latest_jobs(user_profile=user_profile, top_k=self.desired_k)
                if latest_res.success and isinstance(latest_res.data, list) and latest_res.data:
                    final_recommendations = latest_res.data
                    print(f"[FALLBACK] latest_jobs에서 {len(final_recommendations)}개 가져옴")
                else:
                    print("[FALLBACK] latest_jobs에서도 결과를 얻지 못함")
            except Exception as e:
                print(f"[FALLBACK] latest_jobs 호출 중 예외: {e}")

        # 최종 정리
        final_answer = self._compile_final_answer(
            user_profile,
            intent,
            final_recommendations
        )
        
        print(f"\n{'='*60}")
        print(f"🎯 ReAct Agent 완료")
        print(f"{'='*60}\n")
        
        return final_answer
    
    # ================ THOUGHT 단계 ================
    
    def _think(
        self,
        user_profile: Dict[str, Any],
        intent: str,
        current_recommendations: List[Dict],
        past_observations: List[ReActObservation],
        previous_recommendations: List[Dict] = None
    ) -> ReActThought:
        """
        Agent가 생각하기: 현재 상황을 분석하고 다음 액션 결정
        """
        if previous_recommendations is None:
            previous_recommendations = []
        
        # 상황 정보 구성
        profile_summary = self._summarize_profile(user_profile)
        recommendation_status = (
            f"현재 추천 {len(current_recommendations)}개 보유"
            if current_recommendations
            else "추천 결과 없음"
        )
        
        history_summary = ""
        if past_observations:
            success_count = sum(1 for obs in past_observations if obs.success)
            history_summary = f"\n이전 시도: {success_count}/{len(past_observations)} 성공"
        
        # 이전 추천 정보 추가
        previous_context = ""
        if previous_recommendations:
            prev_titles = [r.get('title', '') for r in previous_recommendations[:3]]
            previous_context = f"\n이전 추천 결과 (사용자가 만족하지 않음): {', '.join(prev_titles)}"
            if intent:
                previous_context += f"\n사용자 피드백: '{intent}'"
        
        # LLM 프롬프트 구성
        thought_prompt = f"""
너는 일자리 추천 시스템의 지능형 Agent야.
현재 상황을 분석하고, 다음에 어떤 전략을 써야 할지 판단해.

[현재 상황]
- 사용자 프로필: {profile_summary}
- 사용자 의도: {intent if intent else '없음'}
- {recommendation_status}
{history_summary}
{previous_context}

[사용 가능한 전략]
1. rag_search: 자연어 Query로 의미론적 검색
2. region_specific_search: 지역 기반 정확한 검색
3. experience_based_search: 경험 키워드 기반 검색
4. price_filtered_search: 시급 필터링
5. hybrid_search: RAG + 프로필 필터링 결합
6. latest_jobs: 최신 공고
7. profile_match_filter: 기존 결과 필터링
8. validate_recommendations: 결과 품질 검증

[판단 기준]
- 현재 결과가 0개면: 먼저 기본 검색 시도
- 현재 결과가 1-2개면: 다른 전략으로 더 찾기
- 현재 결과가 3-5개면: 필터링/검증 고려
- 현재 결과가 5개 이상: 종료 고려

[응답 형식 (JSON)]
{{
  "thought": "현재 상황에 대한 분석",
  "next_action": "다음 시도할 전략",
  "reasoning": "왜 그 전략을 선택했는지"
}}

응답:
"""
        
        try:
            response = self.provider.generate_completion({
                "messages": [
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": "일자리 추천 시스템 Agent"}]
                    },
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": thought_prompt}]
                    }
                ],
                "topP": 0.8,
                "topK": 0,
                "maxTokens": 300,
                "temperature": 0.5,
                "repetitionPenalty": 1.1,
                "stop": []
            })
            
            # JSON 파싱
            thought_data = self._parse_json_response(response)
            
            return ReActThought(
                content=thought_data.get("thought", "분석 실패"),
                reasoning=thought_data.get("reasoning", "")
            )
        
        except Exception as e:
            print(f"[ERROR] Thought 생성 실패: {e}")
            return ReActThought(
                content="기본 검색 시도",
                reasoning="Thought 생성 실패로 기본 동작"
            )
    
    # ================ ACTION 단계 ================
    
    def _choose_and_execute_action(
        self,
        thought: ReActThought,
        user_profile: Dict[str, Any],
        intent: str
    ) -> ReActAction:
        """
        Thought를 바탕으로 Tool을 선택하고 params 결정
        """
        # 간단한 휴리스틱 기반 Tool 선택 (실제론 LLM이 선택 가능)
        tool_choice = self._parse_tool_choice(thought.content)
        params = self._build_tool_params(tool_choice, user_profile, intent)
        
        action = ReActAction(tool_choice, params)
        return action
    
    def _parse_tool_choice(self, thought_content: str) -> str:
        """
        Thought 내용에서 Tool 선택 추출
        """
        tool_names = list(self.toolkit.get_available_tools().keys())
        
        # Thought에서 Tool 이름 찾기
        for tool in tool_names:
            if tool in thought_content.lower():
                return tool
        
        # 기본값
        return "rag_search"
    
    def _build_tool_params(
        self,
        tool_name: str,
        user_profile: Dict[str, Any],
        intent: str
    ) -> Dict[str, Any]:
        """
        선택된 Tool에 맞는 parameters 구성
        """
        params = {}
        
        if tool_name == "rag_search":
            # Query 구성
            query_parts = []
            if intent:
                query_parts.append(intent)
            else:
                # 프로필에서 query 생성
                if "experiences" in user_profile:
                    query_parts.append(", ".join(user_profile["experiences"]))
                if "regions" in user_profile:
                    query_parts.append(", ".join(user_profile["regions"]))
            
            params = {
                "query": " ".join(query_parts) if query_parts else "일자리 추천",
                "user_profile": user_profile,
                "top_k": 50  # diversity를 위해 더 많은 후보 가져오기
            }
        
        elif tool_name == "region_specific_search":
            params = {
                "regions": user_profile.get("regions", []),
                "user_profile": user_profile,
                "top_k": 50  # diversity를 위해 더 많은 후보 가져오기
            }
        
        elif tool_name == "experience_based_search":
            params = {
                "experiences": user_profile.get("experiences", []),
                "user_profile": user_profile,
                "top_k": 50  # diversity를 위해 더 많은 후보 가져오기
            }
        
        elif tool_name == "price_filtered_search":
            # Intent에서 시급 정보 추출
            min_wage = self._extract_wage_from_intent(intent, "min", user_profile)
            max_wage = self._extract_wage_from_intent(intent, "max", user_profile)
            
            params = {
                "min_wage": min_wage,
                "max_wage": max_wage,
                "query": intent if intent else "",
                "user_profile": user_profile,
                "top_k": 50  # diversity를 위해 더 많은 후보 가져오기
            }
        
        elif tool_name == "hybrid_search":
            query = intent if intent else self._profile_to_query(user_profile)
            params = {
                "query": query,
                "user_profile": user_profile,
                "top_k": 50  # diversity를 위해 더 많은 후보 가져오기
            }
        
        elif tool_name == "latest_jobs":
            params = {
                "user_profile": user_profile,
                "top_k": 50  # diversity를 위해 더 많은 후보 가져오기
            }
        
        elif tool_name == "profile_match_filter":
            # 이 Tool은 이전 결과를 받아야 함 (다른 곳에서 처리)
            params = {"min_score": 0.4}
        
        elif tool_name == "validate_recommendations":
            params = {
                "min_count": 3,
                "min_avg_score": 0.5
            }
        
        return params
    
    # ================ OBSERVATION 단계 ================
    
    def _analyze_observation(
        self,
        tool_result: ToolResult,
        user_profile: Dict[str, Any],
        current_recommendations: List[Dict]
    ) -> ReActObservation:
        """
        Tool 실행 결과 분석
        """
        if not tool_result.success:
            analysis = f"❌ Tool 실패: {tool_result.message}"
        elif isinstance(tool_result.data, list):
            count = len(tool_result.data)
            if count == 0:
                analysis = "⚠️ 결과 없음 - 다른 전략 필요"
            elif count < 3:
                analysis = f"⚠️ 결과 부족 ({count}개) - 추가 검색 필요"
            else:
                analysis = f"✅ 충분한 결과 ({count}개)"
        else:
            analysis = f"📊 검증 결과: {tool_result.data}"
        
        observation = ReActObservation(tool_result, analysis)
        return observation
    
    # ================ 종료 조건 ================
    
    def _should_stop(
        self,
        thought: ReActThought,
        current_recommendations: List[Dict]
    ) -> bool:
        """
        루프 종료 여부 판단
        """
        # 조건 1: 충분한 결과
        if len(current_recommendations) >= 5:
            return True
        
        # 조건 2: Thought에서 종료 신호
        if "종료" in thought.content or "완료" in thought.content:
            return True
        
        return False
    
    # ================ 최종 답변 ================
    
    def _compile_final_answer(
        self,
        user_profile: Dict[str, Any],
        intent: str,
        recommendations: List[Dict]
    ) -> Dict[str, Any]:
        """
        최종 답변 컴파일
        """
        desired_k = 5
        sorted_recs = sorted(
            recommendations,
            key=lambda x: x.get('match_score', 0),
            reverse=True,
        )
        final_list = [self._sanitize_data(rec) for rec in sorted_recs[:desired_k]]
        print(f"[DIVERSITY] 최종 선택: {len(final_list)}개")
        for i, r in enumerate(final_list, 1):
            print(f"  {i}. {r.get('title')} (job_id={r.get('job_id')}, score={r.get('match_score', 0):.2f})")
        
        return {
            "success": True,
            "recommendations": final_list,
            "reason": self._sanitize_data({
                "iterations": self.iteration_count,
                "thoughts": [t.to_dict() for t in self.thoughts],
                "actions": [a.to_dict() for a in self.actions],
                "observations": [o.to_dict() for o in self.observations]
            })
        }
    
    # ================ Helper Methods ================
    
    def _summarize_profile(self, profile: Dict[str, Any]) -> str:
        """프로필 요약"""
        parts = []
        if "regions" in profile:
            parts.append(f"지역={', '.join(profile['regions'])}")
        if "experiences" in profile:
            parts.append(f"경험={', '.join(profile['experiences'])}")
        if "days" in profile:
            parts.append(f"가능요일={', '.join(profile['days'])}")
        return ", ".join(parts) if parts else "프로필 정보 없음"

    def _normalize_title(self, title: str) -> str:
        """Title normalization for grouping similar titles.

        Lowercase, remove punctuation, and collapse whitespace so that
        small variations map to the same normalized form.
        """
        if not title:
            return ""
        # lowercase
        s = title.lower()
        # remove punctuation (keep unicode word chars and whitespace)
        s = re.sub(r"[^\w\s]", "", s)
        # collapse whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s
    
    def _profile_to_query(self, profile: Dict[str, Any]) -> str:
        """프로필 → 검색 Query"""
        parts = []
        if "experiences" in profile:
            parts.extend(profile["experiences"])
        if "regions" in profile:
            parts.extend(profile["regions"])
        return " ".join(parts) if parts else "일자리 추천"
    
    def _extract_wage_from_intent(
        self,
        intent: str,
        wage_type: str,  # "min" or "max"
        user_profile: Dict[str, Any]
    ) -> int:
        """Intent에서 시급 추출"""
        if not intent:
            return 0 if wage_type == "min" else 99999
        
        # 간단한 패턴 매칭 (실제론 LLM 사용)
        import re
        
        # "15000원", "15000" 패턴 찾기
        numbers = re.findall(r'\d+(?:,\d+)*', intent)
        
        if numbers:
            wage = int(numbers[0].replace(',', ''))
            return wage if wage_type == "min" else 99999
        
        return 0 if wage_type == "min" else 99999
    
    def _merge_recommendations(
        self,
        existing: List[Dict],
        new: List[Dict]
    ) -> List[Dict]:
        """추천 결과 병합 (중복 제거)"""
        existing_ids = {r.get('job_id') for r in existing}
        
        for rec in new:
            if rec.get('job_id') not in existing_ids:
                existing.append(rec)
        
        return existing
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """LLM 응답에서 JSON 추출"""
        try:
            # 1. 코드 블록 추출
            if '```json' in response:
                start = response.find('```json') + len('```json')
                end = response.rfind('```')
                if start > 0 and end > start:
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
            
            # 2. 전체 파싱
            return json.loads(response)
        
        except:
            # 3. 마지막 수단
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                return json.loads(response[start:end])
            except:
                return {
                    "thought": response,
                    "next_action": "rag_search",
                    "reasoning": "JSON 파싱 실패"
                }

    def _sanitize_data(self, value: Any) -> Any:
        """Recursively replace NaN/inf floats with None so JSON serialization works."""
        if isinstance(value, dict):
            return {k: self._sanitize_data(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._sanitize_data(v) for v in value]
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
        return value
