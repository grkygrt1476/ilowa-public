#!/usr/bin/env python3
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()  # .env 파일에서 환경변수 로드

NAVER_CLIENT_ID = os.getenv("NAVER_MAPS_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_MAPS_CLIENT_SECRET", "")

if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
    print("[ERROR] NAVER_MAPS_CLIENT_ID / NAVER_MAPS_CLIENT_SECRET 환경변수를 설정하세요.")
    sys.exit(1)

# 주소 입력 받기: CLI 인자 > 입력 프롬프트
if len(sys.argv) > 1:
    query = " ".join(sys.argv[1:]).strip()
else:
    query = input("검색할 주소를 입력하세요: ").strip()

if not query:
    print("[ERROR] 주소가 비어 있습니다.")
    sys.exit(1)

url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"

headers = {
    "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,     # Client ID
    "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET,    # Client Secret
}

params = {
    "query": query,  # 주소 텍스트
}

print(f"[INFO] 요청 주소: {query}")

try:
    resp = requests.get(url, headers=headers, params=params, timeout=5)
except Exception as e:
    print(f"[ERROR] 요청 실패: {e}")
    sys.exit(1)

print("[INFO] HTTP status:", resp.status_code)

# 원본 응답 텍스트 한번 출력 (디버깅용)
print("=== RAW RESPONSE ===")
print(resp.text)
print("====================")

# JSON 파싱해서 좌표만 깔끔히 보기
try:
    data = resp.json()
except Exception:
    print("[WARN] JSON 파싱 실패")
    sys.exit(0)

if "error" in data:
    # 401, 210 같은 에러일 때
    print("[ERROR] API 에러 발생:")
    print("  errorCode:", data["error"].get("errorCode"))
    print("  message  :", data["error"].get("message"))
    print("  details  :", data["error"].get("details"))
    sys.exit(1)

if data.get("status") == "OK" and data.get("addresses"):
    addr = data["addresses"][0]
    print("\n✅ 첫 번째 결과 요약")
    print("  도로명주소:", addr.get("roadAddress"))
    print("  지번주소 :", addr.get("jibunAddress"))
    print("  경도(x)  :", addr.get("x"))  # x = lng
    print("  위도(y)  :", addr.get("y"))  # y = lat
else:
    print("[INFO] 검색 결과가 없습니다.")
