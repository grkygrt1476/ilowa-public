# """
# ReAct Agent 테스트 스크립트

# ReAct Agent의 기본 동작을 확인하기 위한 테스트
# """
# import sys
# import os

# # 경로 설정
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# from agents.react_agent import ReActAgent


# def test_basic_recommendation():
#     """기본 추천 테스트"""
#     print("\n" + "="*60)
#     print("🧪 Test 1: 기본 추천")
#     print("="*60)
    
#     agent = ReActAgent("data/new_work_with_embeddings.csv")
    
#     user_profile = {
#         "nickname": "김할머니",
#         "regions": ["서울"],
#         "days": ["월", "화", "수"],
#         "time_slots": ["오전"],
#         "experiences": ["청소"],
#         "capabilities": {"체력": 5, "기술": 2}
#     }
    
#     result = agent.run(user_profile=user_profile, intent="")
    
#     print(f"\n✅ 최종 결과:")
#     print(f"   추천 개수: {len(result.get('recommendations', []))}")
#     print(f"   반복 횟수: {result.get('reason', {}).get('iterations', 0)}")
    
#     if result.get('recommendations'):
#         print(f"\n   상위 3개 추천:")
#         for i, rec in enumerate(result['recommendations'][:3], 1):
#             print(f"   {i}. {rec.get('title', 'N/A')} - {rec.get('place', 'N/A')} ({rec.get('match_score', 0)}%)")
    
#     return result


# def test_voice_intent_recommendation():
#     """음성 의도 포함 추천 테스트"""
#     print("\n" + "="*60)
#     print("🧪 Test 2: 음성 의도 포함 추천")
#     print("="*60)
    
#     agent = ReActAgent("data/new_work_with_embeddings.csv")
    
#     user_profile = {
#         "nickname": "박할아버지",
#         "regions": ["부산"],
#         "days": ["월", "화", "수", "목"],
#         "time_slots": ["오전", "오후"],
#         "experiences": ["배송", "택배"],
#         "capabilities": {"체력": 4, "기술": 3}
#     }
    
#     # 추가 요청
#     intent = "시급 12000원 이상, 주말은 안 돼"
    
#     result = agent.run(user_profile=user_profile, intent=intent)
    
#     print(f"\n✅ 최종 결과:")
#     print(f"   의도: '{intent}'")
#     print(f"   추천 개수: {len(result.get('recommendations', []))}")
#     print(f"   반복 횟수: {result.get('reason', {}).get('iterations', 0)}")
    
#     if result.get('recommendations'):
#         print(f"\n   상위 3개 추천:")
#         for i, rec in enumerate(result['recommendations'][:3], 1):
#             print(f"   {i}. {rec.get('title', 'N/A')} - {rec.get('hourly_wage', 'N/A')}원 ({rec.get('match_score', 0)}%)")
    
#     return result


# def test_tool_toolkit():
#     """Tool Toolkit 기본 동작 테스트"""
#     print("\n" + "="*60)
#     print("🧪 Test 3: Tool Toolkit 동작")
#     print("="*60)
    
#     from agents.tools.toolkit import AgentToolkit
    
#     toolkit = AgentToolkit("data/new_work_with_embeddings.csv")
    
#     # 사용 가능한 Tool 확인
#     print("\n📋 사용 가능한 Tool:")
#     for tool_name, description in toolkit.get_available_tools().items():
#         print(f"   - {tool_name}: {description}")
    
#     # RAG Search 테스트
#     print("\n🔧 RAG Search 테스트:")
#     user_profile = {"regions": ["서울"], "experiences": ["청소"]}
#     result = toolkit.rag_search(
#         query="서울 청소 일자리",
#         user_profile=user_profile,
#         top_k=3
#     )
#     print(f"   결과: {len(result.data)}개 (성공: {result.success})")
    
#     # Region-Specific Search 테스트
#     print("\n🔧 Region-Specific Search 테스트:")
#     result = toolkit.region_specific_search(
#         regions=["서울"],
#         user_profile=user_profile,
#         top_k=3
#     )
#     print(f"   결과: {len(result.data)}개 (성공: {result.success})")
    
#     # Hybrid Search 테스트
#     print("\n🔧 Hybrid Search 테스트:")
#     result = toolkit.hybrid_search(
#         query="청소 일자리",
#         user_profile=user_profile,
#         top_k=5
#     )
#     print(f"   결과: {len(result.data)}개 (성공: {result.success})")


# def test_graph_integration():
#     """LangGraph 통합 테스트"""
#     print("\n" + "="*60)
#     print("🧪 Test 4: LangGraph 통합")
#     print("="*60)
    
#     from agents.graph_builder import build_graph
    
#     graph = build_graph()
    
#     initial_state = {
#         "user_profile": {
#             "nickname": "이할머니",
#             "regions": ["서울"],
#             "days": ["월", "화"],
#             "time_slots": ["오전"],
#             "experiences": ["청소"],
#             "capabilities": {}
#         },
#         "intent": "",
#         "voice_context": "",
#         "recommendations": [],
#         "reasoning": {}
#     }
    
#     print("\n🚀 Graph 실행...")
#     result_state = graph.invoke(initial_state)
    
#     print(f"\n✅ 그래프 실행 완료:")
#     print(f"   추천 개수: {len(result_state.get('recommendations', []))}")
#     print(f"   추론 정보: {bool(result_state.get('reasoning', {}))}")


# if __name__ == "__main__":
#     print("\n🤖 ReAct Agent 통합 테스트 시작\n")
    
#     try:
#         # 기본 테스트는 항상 실행
#         test_basic_recommendation()
#         test_voice_intent_recommendation()
#         test_tool_toolkit()
        
#         # Graph 통합은 선택적 (LangGraph 설치 필요)
#         try:
#             test_graph_integration()
#         except ImportError:
#             print("\n⚠️  LangGraph 테스트 건너뜀 (import 실패)")
        
#         print("\n" + "="*60)
#         print("✅ 모든 테스트 완료!")
#         print("="*60 + "\n")
    
#     except Exception as e:
#         print(f"\n❌ 테스트 실패: {e}")
#         import traceback
#         traceback.print_exc()
