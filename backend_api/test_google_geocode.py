#!/usr/bin/env python3
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = (
    os.getenv("GOOGLE_GEOCODING_API_KEY")
    or os.getenv("GOOGLE_GEOCODING")
)

if not API_KEY:
    print("[ERROR] GOOGLE_GEOCODING_API_KEY (또는 GOOGLE_GEOCODING) 환경변수를 설정하세요.")
    sys.exit(1)

if len(sys.argv) > 1:
    query = " ".join(sys.argv[1:]).strip()
else:
    query = input("검색할 주소를 입력하세요: ").strip()

if not query:
    print("[ERROR] 주소가 비어 있습니다.")
    sys.exit(1)

url = "https://maps.googleapis.com/maps/api/geocode/json"
params = {
    "address": query,
    "key": API_KEY,
    "language": "ko",
}

print(f"[INFO] 요청 주소: {query}")

try:
    resp = requests.get(url, params=params, timeout=5)
except Exception as exc:
    print(f"[ERROR] 요청 실패: {exc}")
    sys.exit(1)

print("[INFO] HTTP status:", resp.status_code)
print("=== RAW RESPONSE ===")
print(resp.text)
print("====================")

try:
    data = resp.json()
except Exception:
    print("[WARN] JSON 파싱 실패")
    sys.exit(0)

status = data.get("status")
if status != "OK":
    print(f"[ERROR] status={status} message={data.get('error_message')}")
    sys.exit(1)

results = data.get("results") or []
if not results:
    print("[INFO] 검색 결과가 없습니다.")
    sys.exit(0)

best = results[0]
geom = best.get("geometry", {})
loc = geom.get("location", {})

print("\n✅ 첫 번째 결과 요약")
print("  정규화 주소:", best.get("formatted_address"))
print("  경도(x)    :", loc.get("lng"))
print("  위도(y)    :", loc.get("lat"))
