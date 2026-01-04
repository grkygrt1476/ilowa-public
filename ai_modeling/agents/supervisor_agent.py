# import json
# from typing import Dict, Any, List
# from services.clova_llm import CompletionExecutor
# from agents.recommender_agent import RecommenderAgent


# class SupervisorAgent:
#     """
#     Supervisor Agent: 계획 수립 및 실행 관리
#     1차 추천: 프로필 기반 계획 생성
#     2차 추천: 프로필 + 음성 의도 결합 계획 생성
#     """

#     def __init__(self, recommender: RecommenderAgent):
#         self.recommender = recommender
#         self.llm = CompletionExecutor()

#     def _build_plan_prompt(self, goal: Dict[str, Any]) -> str:
#         """
#         LLM에게 계획(plan)을 JSON으로 만들게 하는 프롬프트
#         """
#         user_profile = goal.get("user_profile", {})
#         intent = goal.get("intent", "")
#         voice_context = goal.get("voice_context")
        
#         # 프로필 정보 자연어로 풀어서 작성
#         profile_text = f"""
# 사용자는 {', '.join(user_profile.get('regions', ['미정']))} 지역을 선호하며, 
# {', '.join(user_profile.get('days', ['미정']))} 요일에 가능한 업무를 선호합니다. 
# 또한, {', '.join(user_profile.get('time_slots', ['미정']))} 시간대를 선호합니다.
# 사용자는 {', '.join(user_profile.get('experiences', ['미정']))} 경험이 있으며, 
# {user_profile.get('capabilities', '미정')} 능력치를 가지고 있습니다.
# """
        
#         # 음성 의도가 있으면 추가
#         if intent or voice_context:
#             profile_text += f"\n- 추가 요청: {intent or voice_context}"

#         prompt = f"""

# 너는 일자리 추천 시스템의 계획 수립자(Supervisor)야.
# 사용자 정보를 분석해서 추천 작업 계획을 JSON으로 생성해줘.

# 사용자 정보:
# {profile_text}

# 계획 JSON 스키마:
# {{
#   "steps": [
#     {{
#       "action": "recommend",
#       "input": "사용자는 {', '.join(user_profile.get('regions', ['미정']))} 지역을 선호하고, {', '.join(user_profile.get('time_slots', ['미정']))} 시간대에 {', '.join(user_profile.get('experiences', ['미정']))} 일을 찾고 있다고 알려주는 정보를 바탕으로 적합한 일자리를 추천"
#     }},
#     {{
#       "action": "finish",
#       "input": ""
#     }}
#   ],
#   "notes": "사용자의 지역, 직무, 시간대에 맞는 일자리 추천"
# }}

# 규칙:
# 1. "recommend" action에서 input은 자연어로 작성된 검색 쿼리. 예: "사용자는 서울 강남에서 오전 시간대에 청소 일을 찾고 있다고 알려주는 정보를 바탕으로 적합한 일자리를 추천"
# 2. 사용자 지역, 직무, 시간대를 반영한 자연어 쿼리 작성
# 3. 음성 요청이 있으면 그것도 반영
# 4. 마지막은 항상 "finish" action
# 5. JSON만 출력, 다른 설명 없이

# 출력:

# """
#         return prompt

#     def plan_with_llm(self, goal: Dict[str, Any]) -> Dict[str, Any]:
#         """
#         LLM으로 계획 생성
#         """
#         prompt = self._build_plan_prompt(goal)
#         request_data = {
#             "messages": [
#                 {"role": "system", "content": [{"type": "text", "text": "일자리 추천 계획 수립 전문가"}]},
#                 {"role": "user", "content": [{"type": "text", "text": prompt}]}
#             ],
#             "topP": 0.8,
#             "topK": 0,
#             "maxTokens": 500,
#             "temperature": 0.3,
#             "repetitionPenalty": 1.1,
#             "stop": []
#         }

#         try:
#             resp_text = self.llm.execute(request_data)
#             print(f"LLM 응답: {resp_text}") # 응답 전체 출력 (디버깅용)

#             # 1. JSON 코드 블록 추출 시도 (가장 안정적)
#             json_str = None
#             if '```json' in resp_text:
#                 json_start = resp_text.find('```json') + len('```json')
#                 json_end = resp_text.rfind('```')
                
#                 if json_start != -1 and json_end != -1 and json_end > json_start:
#                     json_str = resp_text[json_start:json_end].strip().lstrip('\n').rstrip('\n')
            
#             if json_str:
#                 parsed = json.loads(json_str)
#                 print("[INFO] Successfully parsed JSON from code block.")
#                 return parsed
                
#             # 2. 코드 블록이 없거나 추출 실패 시, 전체 응답을 직접 파싱 시도
#             parsed = json.loads(resp_text)
#             return parsed
            
#         except Exception as e:
#             # LLM 통신 오류, 1차 파싱 실패, 코드 블록 내 파싱 오류 등 모든 예외 처리
#             print(f"LLM 응답 처리 중 오류 발생: {e}")
            
#             # 3. JSON 추출 재시도 (최후의 수단: {}로 감싸진 부분만 찾기)
#             try:
#                 start = resp_text.find('{')
#                 end = resp_text.rfind('}')
#                 if start != -1 and end != -1 and end > start:
#                     parsed = json.loads(resp_text[start:end + 1])
#                     print("[INFO] Successfully extracted and parsed JSON as a fallback.")
#                     return parsed
#             except Exception as e_extract:
#                 print(f"JSON 추출 중 최종 오류 발생: {e_extract}")
#                 pass # 최종 실패 -> Fallback Plan 실행
#         # Fallback plan
#         user_profile = goal.get("user_profile", {})
#         intent = goal.get("intent", "")
        
#         # 지역, 가능한 요일, 시간대, 경험, 능력치 모두 자연어로 풀어서 쿼리 생성
#         regions = ', '.join(user_profile.get('regions', ['미정']))
#         days = ', '.join(user_profile.get('days', ['미정']))
#         time_slots = ', '.join(user_profile.get('time_slots', ['미정']))
#         experiences = ', '.join(user_profile.get('experiences', ['미정']))
#         capabilities = user_profile.get('capabilities', '미정')

#         fallback_input = (
#             f"사용자는 {regions} 지역을 선호하며, "
#             f"{days} 요일에 가능한 업무를 선호합니다. "
#             f"또한, {time_slots} 시간대에 가능한 일을 찾고 있습니다. "
#             f"경험으로는 {experiences}가 있으며, 능력치는 {capabilities}입니다."
#         )

#         if intent:
#             fallback_input = f"{fallback_input} 또한 {intent} 요청을 반영해 주세요."

#         return {
#             "steps": [
#                 {"action": "recommend", "input": fallback_input},
#                 {"action": "finish", "input": ""}
#             ],
#             "notes": "Fallback plan (LLM 실패)"
#         }

#     def execute_plan(self, plan: Dict[str, Any], goal: Dict[str, Any], max_steps: int = 5) -> Dict[str, Any]:
#         """
#         계획 실행
#         """
#         out = {"executed_steps": [], "final": None}
#         steps = plan.get("steps", [])
#         step_count = 0
        
#         for step in steps:
#             if step_count >= max_steps:
#                 break
            
#             action = step.get("action")
#             inp = step.get("input", "")
#             print("!!!!!!!!!!!!!!!!1inp", inp)
#             if action == "recommend":
#                 # Recommender에게 검색 위임
#                 recs = self.recommender.recommend(
#                     query=inp,
#                     user_profile=goal.get("user_profile", {}),
#                     top_k=5
#                 )
#                 out["executed_steps"].append({
#                     "action": "recommend",
#                     "input": inp,
#                     "result": recs
#                 })
            
#             elif action == "finish":
#                 out["final"] = step.get("input", "")
#                 out["executed_steps"].append({
#                     "action": "finish",
#                     "input": inp
#                 })
#                 break
            
#             else:
#                 out["executed_steps"].append({
#                     "action": action,
#                     "input": inp,
#                     "result": "unsupported_action"
#                 })
            
#             step_count += 1
        
#         if out["final"] is None and out["executed_steps"]:
#             out["final"] = out["executed_steps"][-1].get("result")
        
#         return out


# # ==================== LangGraph Node 함수 ====================
# def supervisor_node(state):
#     """
#     LangGraph Node: Supervisor
#     상태에서 user_profile과 intent를 받아 계획 수립
#     """
#     from agents.recommender_agent import RecommenderAgent
    
#     recommender = RecommenderAgent("data/new_work_with_embeddings.csv")
#     supervisor = SupervisorAgent(recommender)
    
#     # 목표 설정
#     goal = {
#         "user_profile": state.get("user_profile", {}),
#         "intent": state.get("intent", ""),
#         "voice_context": state.get("voice_context")
#     }
    
#     # 계획 수립
#     plan = supervisor.plan_with_llm(goal)
    
#     # 계획 실행
#     execution = supervisor.execute_plan(plan, goal)
    
#     # 상태 업데이트
#     state["plan"] = plan
#     state["recommendations"] = []
    
#     # executed_steps에서 추천 결과 추출
#     for step in execution.get("executed_steps", []):
#         if step["action"] == "recommend" and isinstance(step.get("result"), list):
#             state["recommendations"].extend(step["result"])
    
#     return state
