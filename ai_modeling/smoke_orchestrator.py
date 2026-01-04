# ai_modeling/smoke_orchestrator.py
from dotenv import load_dotenv
load_dotenv()

from orchestration import AIModelingOrchestrator

def main():
    orch = AIModelingOrchestrator(provider_name="naver")

    user_profile = {
        "nickname": "홍길동",
        "regions": ["서울 종로구"],
        "days": ["월", "수"],
        "time_slots": ["오전"],
        "experiences": ["마트 진열"],
        "capabilities": {"physical": "보통"},
    }

    print("=== 추천 테스트 ===")
    rec = orch.recommend(user_profile=user_profile, intent="가벼운 실내 소일거리")
    print(rec.keys())
    print("provider:", rec.get("provider"))

if __name__ == "__main__":
    main()

