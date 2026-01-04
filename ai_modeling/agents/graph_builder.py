# from typing import TypedDict, List, Dict, Any
# from langgraph.graph import StateGraph, END
# from agents.react_agent import ReActAgent


# # ✅ LangGraph에서 관리할 State 정의
# class AgentState(TypedDict):
#     user_profile: Dict[str, Any]      # 사용자 프로필
#     intent: str                        # 음성 의도 (2차 추천 시 사용)
#     voice_context: str                 # 음성 컨텍스트 (옵션)
#     recommendations: List[Dict]        # 최종 추천 결과
#     reasoning: Dict[str, Any]          # ReAct 추론 과정


# # ✅ ReAct 기반 Node 정의
# def react_node(state: AgentState) -> AgentState:
#     """
#     ReAct Agent 실행 Node
    
#     Thought → Action → Observation 루프를 통해
#     자율적으로 최적의 추천을 생성
#     """
#     agent = ReActAgent("data/new_work_with_embeddings.csv")
    
#     result = agent.run(
#         user_profile=state.get("user_profile", {}),
#         intent=state.get("intent", "")
#     )
    
#     state["recommendations"] = result.get("recommendations", [])
#     state["reasoning"] = result.get("reason", {})
    
#     return state


# # ✅ LangGraph Graph 빌더 (ReAct 방식)
# def build_graph():
#     """
#     LangGraph 기반 ReAct 추천 플로우:
    
#     START → react_agent (Thought→Action→Observation 루프) → END
    
#     ReAct Agent는 내부적으로:
#     1. 상황 분석 (Thought)
#     2. 도구 선택 및 실행 (Action)
#     3. 결과 평가 (Observation)
#     를 반복하면서 최적의 추천을 찾음
#     """
#     workflow = StateGraph(AgentState)

#     # ====== Node 등록 ======
#     workflow.add_node("react_agent", react_node)

#     # ====== 흐름 정의 ======
#     workflow.set_entry_point("react_agent")
#     workflow.add_edge("react_agent", END)

#     return workflow.compile()