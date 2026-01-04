# # agents/recommender_agent.py
# from agents.tools.csv_rag_tool import CSVRAGTool
# from typing import Dict, Any, List


# class RecommenderAgent:
#     """
#     Recommender Agent: CSV RAG 기반 일자리 추천
#     """
    
#     def __init__(self, csv_path: str = "data/new_work_with_embeddings.csv"):
#         self.csv_tool = CSVRAGTool(csv_path)

#     def recommend(self, query: str, user_profile: dict = None, top_k: int = 5) -> List[Dict]:
#         """
#         단일 추천 호출
#         - query: 검색 쿼리 (Supervisor가 생성)
#         - user_profile: 사용자 프로필 (필터링/매칭용)
#         - top_k: 상위 K개 결과
#         """
#         if not query or not query.strip():
#             return []
        
#         # 1️⃣ 프로필 정보를 자연어로 통합 (검색 품질 향상)
#         profile_text = ""
#         if user_profile:
#             if "regions" in user_profile:
#                 profile_text += " 지역: " + ", ".join(user_profile["regions"])
#             if "days" in user_profile:
#                 profile_text += " 요일: " + ", ".join(user_profile["days"])
#             if "time_slots" in user_profile:
#                 profile_text += " 시간대: " + ", ".join(user_profile["time_slots"])
#             if "experiences" in user_profile:
#                 profile_text += " 경험: " + ", ".join(user_profile["experiences"])
        
#         # 자연어 query + 프로필 통합
#         full_query = query
#         if profile_text:
#             full_query += " | " + profile_text
        
#         # 2️⃣ RAG 검색
#         results = self.csv_tool.query(full_query, top_k=top_k)
        
#         # 3️⃣ 추천 이유 추가
#         for result in results:
#             reason_parts = []
#             score = result.get('score', 0)
            
#             # 지역 매칭
#             if user_profile and "regions" in user_profile:
#                 job_address = result.get('address', '')
#                 if any(region in job_address for region in user_profile["regions"]):
#                     reason_parts.append("지역 일치")
            
#             # 경험 매칭
#             if user_profile and "experiences" in user_profile:
#                 job_title = result.get('title', '')
#                 if any(exp in job_title for exp in user_profile["experiences"]):
#                     reason_parts.append("경험 일치")
            
#             result['recommendation_reason'] = ', '.join(reason_parts) if reason_parts else "유사도 기반"
#             result['match_score'] = round(score * 100, 1)
        
#         return results

#     def execute(self, inputs: dict):
#         """
#         Backward-compatible execute (레거시)
#         """
#         return {
#             "recommendations": self.recommend(
#                 inputs.get("intent", ""),
#                 inputs.get("user_profile", {})
#             )
#         }


# # ==================== LangGraph Node 함수 ====================
# def recommender_node(state):
#     """
#     LangGraph Node: Recommender
#     Supervisor가 이미 추천을 완료했으므로 여기서는 추가 작업만 수행
#     (예: 후처리, 정렬, 필터링 등)
#     """
#     # 이미 supervisor에서 추천이 완료되어 state["recommendations"]에 저장됨
#     # 필요하면 여기서 추가 처리 가능
    
#     # 예: 점수 기준 재정렬
#     if state.get("recommendations"):
#         state["recommendations"] = sorted(
#             state["recommendations"],
#             key=lambda x: x.get("match_score", 0),
#             reverse=True
#         )
    
#     return state