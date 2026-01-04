import os
import json
import sys
import uuid
import http.client
import time
from dotenv import load_dotenv

load_dotenv()

CLOVA_LLM_API_KEY = os.getenv("CLOVA_LLM_API_KEY")
CLOVA_LLM_URL = os.getenv("CLOVA_LLM_URL")
import re

_host_match = re.match(r"https?://([^/]+)", CLOVA_LLM_URL or "")
CLOVA_EMBED_HOST = _host_match.group(1) if _host_match else "clovastudio.stream.ntruss.com"
REQUEST_PATH = "/v1/api-tools/embedding/clir-emb-dolphin"

class EmbeddingExecutor:
    def __init__(self):
        self._host = CLOVA_EMBED_HOST
        self._api_key = f"Bearer {CLOVA_LLM_API_KEY}"
        self._request_id = str(uuid.uuid4())

    def get_embedding(self, text: str):
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': self._api_key,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id
        }
        payload = {"text": text}

        try:
            conn = http.client.HTTPSConnection(self._host)
            conn.request('POST', REQUEST_PATH, json.dumps(payload), headers)
            res = conn.getresponse()
            data = json.loads(res.read().decode("utf-8"))
            conn.close()

            # Check for successful response
            if data.get("status", {}).get("code") == "20000":
                embedding = data["result"].get("embedding", [])
                print(f"[DEBUG] Embedding 차원: {len(embedding)}")  # 차원 확인
                return embedding
            # Handle rate limit exceeded error (42901)
            elif data.get("status", {}).get("code") == "42901":
                print(f"[ERROR] Rate limit 초과: 재시도 시도...")
                # Retry after the rate limit reset time
                retry_after = int(res.getheader('X-RateLimit-Reset', 60))  # Default retry after 60 seconds
                time.sleep(retry_after)
                return self.get_embedding(text)  # Retry the request
            else:
                print(f"[ERROR] Embedding API 오류: {data}")
                return []
        except Exception as e:
            print(f"[ERROR] Embedding 생성 실패: {e}")
            return []

# Use the EmbeddingExecutor class
_executor = EmbeddingExecutor()

def get_clova_embedding(text: str):
    return _executor.get_embedding(text)

# CSV Embedding 재생성

import pandas as pd
import argparse
from typing import Optional

parser = argparse.ArgumentParser(description="Rebuild embeddings from CSV or JSON using CLOVA")
parser.add_argument("--input", default='data/new_work_with_embeddings_openai_backup.csv', help="input CSV or JSON path")
parser.add_argument("--output", default='data/new_work_with_embeddings_clova.csv', help="output CSV path")
parser.add_argument("--skip-existing", action='store_true', help="skip rows that already have non-empty embedding")
parser.add_argument("--force", action='store_true', help="force re-embedding of all rows (ignore existing embedding)")
parser.add_argument("--clear-embeddings", action='store_true', help="clear embedding column before processing")
args = parser.parse_args()

input_file = args.input
output_file = args.output
skip_existing = args.skip_existing and not args.force
force_reembed = args.force
clear_embeddings_before = args.clear_embeddings

try:
    # Check file extension
    if input_file.lower().endswith('.json'):
        # Load JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        print(f"✅ JSON 로드 완료: {len(df)}개 행 (from {input_file})")
    elif input_file.lower().endswith('.csv'):
        df = pd.read_csv(input_file)
        print(f"✅ CSV 로드 완료: {len(df)}개 행 (from {input_file})")
    else:
        print(f"❌ 지원하지 않는 파일 형식입니다. .csv 또는 .json 파일을 사용하세요.")
        sys.exit(1)
except Exception as e:
    print(f"❌ 파일 로드 실패: {e}")
    exit(1)

success_count = 0
fail_count = 0

# If requested, clear embedding column before processing
if clear_embeddings_before:
    print("--clear-embeddings specified: clearing existing embedding column values")
    df['embedding'] = ''

# Simple heuristic used when LLM is not available or fails
# Require LLM for stamina classification (user requested no heuristic)
def classify_stamina_with_llm(text: str) -> Optional[str]:
    if not CLOVA_LLM_API_KEY or not CLOVA_LLM_URL:
        print("[ERROR] CLOVA_LLM_API_KEY or CLOVA_LLM_URL not set. LLM-only mode requires these env vars.")
        sys.exit(1)
    try:
        # Try relative import first, then absolute
        try:
            from services.clova_llm import CompletionExecutor
        except ImportError:
            from ai_modeling.services.clova_llm import CompletionExecutor
        execr = CompletionExecutor()
        prompt = (
            "아래 공고의 제목/설명/장소/클라이언트를 읽고, 이 업무의 체력 요구도를 '상'/'중'/'하' 중 하나로만 출력하세요.\n\n공고:\n" + text + "\n\n(출력은 반드시 '상' 또는 '중' 또는 '하' 한 글자만)"
        )
        request = {
            "messages": [
                {"role": "system", "content": [{"type":"text","text":"체력 요구도 분류기"}]},
                {"role": "user", "content": [{"type":"text","text": prompt}]}
            ],
            "topP": 0.8,
            "topK": 0,
            "temperature": 0.0,
            "maxTokens": 10,
            "stream": False
        }
        resp = execr.execute(request)
        if not resp:
            print("[ERROR] LLM returned empty response for stamina classification")
            return None
        for ch in resp:
            if ch in ["상", "중", "하"]:
                return ch
        for tok in str(resp).split():
            if tok in ["상", "중", "하"]:
                return tok
        print(f"[ERROR] Unable to parse LLM response for stamina: {resp}")
        return None
    except Exception as e:
        print(f"[ERROR] LLM classification failed: {e}")
        return None

# 각 행의 embedding을 CLOVA로 재생성
for idx, row in df.iterrows():
    # ALWAYS ensure stamina_level exists: if missing or nan, use LLM to classify
    stamina = None
    stamina_val = str(row.get('stamina_level', '')).strip()
    # Check if stamina_level exists and is not empty/nan
    if 'stamina_level' in row.index and stamina_val and stamina_val.lower() not in ['nan', 'none', '']:
        stamina = row.get('stamina_level')
        print(f"[INFO] Row {idx} already has stamina_level={stamina}")
    else:
        # build short text to classify
        text_for_class = " ".join([str(row.get(k, "")) for k in ['title', 'description', 'place', 'client']])
        print(f"[INFO] Row {idx} calling LLM to classify stamina_level...")
        stamina = classify_stamina_with_llm(text_for_class)
        if not stamina:
            print(f"[ERROR] LLM failed to classify stamina for row {idx}. Aborting due to LLM-only policy.")
            sys.exit(1)
        # write back into dataframe so output CSV contains the label
        try:
            df.at[idx, 'stamina_level'] = stamina
        except Exception:
            # if df doesn't have the column, create it
            df.loc[idx, 'stamina_level'] = stamina
        print(f"[INFO] Row {idx} classified as stamina_level={stamina}")
        # Wait after LLM call to avoid rate limiting
        time.sleep(1)

    # Skip embedding generation ONLY if --skip-existing AND embedding exists AND stamina was already set (and not nan)
    # Otherwise, regenerate embedding with stamina_level included
    has_embedding = str(row.get('embedding', '')).strip()
    stamina_check = str(row.get('stamina_level', '')).strip()
    if skip_existing and has_embedding and stamina_check and stamina_check.lower() not in ['nan', 'none', '']:
        print(f"[SKIP] Row {idx} already has both embedding and stamina_level")
        continue

    # 텍스트 조합 (stamina_level 컬럼 포함)
    parts = [
        f"제목은 {row.get('title', '')}입니다.",
        f"참여자 수는 {row.get('participants', '')}명입니다.",
        f"시급은 {row.get('hourly_wage', '')}원입니다.",
        f"장소는 {row.get('place', '')}입니다.",
        f"주소는 {row.get('address', '')}입니다.",
        f"근무 요일은 {row.get('work_days', '')}입니다.",
        f"시작 시간은 {row.get('start_time', '')}입니다.",
        f"종료 시간은 {row.get('end_time', '')}입니다.",
        f"클라이언트는 {row.get('client', '')}입니다.",
        f"설명: {row.get('description', '')}",
        f"체력난이도는 {stamina}입니다."
    ]

    text_for_embedding = " ".join(parts)

    # 텍스트가 비어있는 경우 건너뛰기
    if not text_for_embedding.strip():
        print(f"[INFO] Row {idx} skipped (empty text)")
        fail_count += 1
        continue

    # CLOVA Embedding 생성
    try:
        new_embedding = get_clova_embedding(text_for_embedding)
        if new_embedding and len(new_embedding) == 1024:
            # 리스트를 문자열로 저장
            df.at[idx, 'embedding'] = "[" + ", ".join(str(x) for x in new_embedding) + "]"
            success_count += 1
            if (idx + 1) % 10 == 0:
                print(f"✅ 진행: {idx + 1}/{len(df)} ({success_count} 성공, {fail_count} 실패)")
        else:
            fail_count += 1
            print(f"⚠️ Row {idx} Embedding 생성 실패 (길이: {len(new_embedding) if new_embedding else 0})")
    except Exception as e:
        fail_count += 1
        print(f"❌ Row {idx} 오류: {e}")

    # API 속도 제한 방지
    if (idx + 1) % 10 == 0:
        time.sleep(1)  # 1초 대기

# 새 CSV 저장
try:
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n=== ✅ 완료! ===")
    print(f"새 파일 저장: {output_file}")
    print(f"성공: {success_count}개, 실패: {fail_count}개")

    # 검증
    verify_df = pd.read_csv(output_file)
    verify_emb = eval(verify_df.iloc[0]['embedding'])
    print(f"검증: 새 파일 첫 번째 행 Embedding 차원 = {len(verify_emb)}")
except Exception as e:
    print(f"❌ 저장 실패: {e}")
