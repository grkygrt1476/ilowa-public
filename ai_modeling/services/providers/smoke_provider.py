# ai_modeling/smoke_provider.py
from dotenv import load_dotenv
load_dotenv()

from ai_modeling.services.providers import get_ai_provider

def main():
    provider = get_ai_provider("naver")
    print("✅ provider:", provider.name)

    # LLM 테스트
    res = provider.generate_completion({
        "messages": [
            {"role": "system", "content": "너는 시니어 소일거리 추천 도우미야."},
            {"role": "user", "content": "65세 이상 어르신이 할 수 있는 가벼운 동네 일 2개만 말해줘."},
        ],
        "stream": False,
    })
    print("LLM 응답:", res[:200], "...\n")

    # Embedding 테스트
    emb = provider.embed_text("동네 마트 진열 보조")
    print("임베딩 길이:", len(emb))

if __name__ == "__main__":
    main()
