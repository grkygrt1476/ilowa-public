import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLOVA_STT_URL = os.getenv("CLOVA_STT_URL", "clovastturl")
CLOVA_STT_SECRET = os.getenv("CLOVA_STT_SECRET")
# For local/offline testing you can set STT_MOCK_TEXT to have the STT return a
# deterministic transcription without calling the external service.
STT_MOCK_TEXT = os.getenv("STT_MOCK_TEXT")

def clova_stt_from_file(file_path: str, lang: str = "Kor"):
    """
    로컬 파일을 CLOVA STT에 업로드하고 동기(sync) 방식으로 결과 반환
    lang 값은 문서에 따라 'Kor', 'Eng', 'Jpn', 'Chn' 중 하나여야 함.
    """
    # If a mock transcription is provided via env, use it (offline testing)
    if STT_MOCK_TEXT:
        return {"text": STT_MOCK_TEXT}

    # If no secret is configured, return empty transcription and log a warning
    if not CLOVA_STT_SECRET or not CLOVA_STT_URL:
        print("CLOVA STT 인증정보가 설정되지 않았습니다. STT 호출을 건너뜁니다.")
        return {"text": ""}

    headers = {
        "X-CLOVASPEECH-API-KEY": CLOVA_STT_SECRET,
        "Content-Type": "application/octet-stream"
    }

    # 쿼리 파라미터로 lang 전달
    params = {
        "lang": lang
    }

    with open(file_path, "rb") as f:
        audio_data = f.read()

    resp = requests.post(
        CLOVA_STT_URL,
        headers=headers,
        params=params,
        data=audio_data,
        timeout=60
    )

    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("HTTP 오류 발생:", e)
        print("응답 내용:", resp.text)
        return {"text": ""}

    result = resp.json()
    text = result.get("text", "")
    return {"text": text}


if __name__ == "__main__":
    file_path = os.path.join("sample", "test_voice.mp3")
    print("=== CLOVA STT 호출 중... ===")
    stt_result = clova_stt_from_file(file_path)
    print("\n=== STT 인식 결과 ===")
    print(stt_result["text"])
