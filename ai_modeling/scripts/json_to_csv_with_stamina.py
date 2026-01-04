#!/usr/bin/env python3
"""
Convert a JSON seed of job posts into the CSV used for embedding regeneration,
and add a `stamina_level` column (상/중/하). If CLOVA LLM credentials are present
the script will call the repo's LLM client for classification; otherwise a
lightweight keyword heuristic is used.

Output path (default): ai_modeling/data/new_work_with_embeddings_openai_backup.csv

Usage:
  python json_to_csv_with_stamina.py [path/to/job_seed.json]

"""
import os
import sys
import json
import csv
from pathlib import Path
from dotenv import load_dotenv
import argparse
import subprocess
import time
from typing import Optional

import pandas as pd
import http.client
import uuid
import re

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data" / "job_seed_seniorforum_100.json"
# canonical intermediate CSV produced from JSON seed
DEFAULT_OUT = ROOT / "data" / "new_work_with_embeddings_from_seed.csv"


def main():
    parser = argparse.ArgumentParser(description="Convert JSON seed to CSV for embeddings")
    parser.add_argument("input", nargs="?", default=str(DEFAULT_IN), help="input JSON path")
    parser.add_argument("--output", default=str(DEFAULT_OUT), help="output CSV path")
    parser.add_argument("--no-embed", action="store_true", help="Do not run embedding step after conversion (default: run)")
    parser.add_argument("--embed-output", default=str(ROOT / "data" / "new_work_with_embeddings_clova.csv"), help="output CSV path for embedding step")
    parser.add_argument("--clear-embeddings", action='store_true', help="clear embedding column before processing in embedding step")
    parser.add_argument("--force", action='store_true', help="force re-embedding of all rows (ignore existing embedding)")
    parser.add_argument("--skip-existing", action='store_true', help="skip rows that already have non-empty embedding")
    parser.add_argument("--rebuild-args", default="", help="(deprecated) kept for compatibility")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        print(f"Input JSON not found: {in_path}")
        sys.exit(1)

    try:
        jobs = json.loads(in_path.read_text(encoding="utf-8"))
    except Exception as e:
        print("Failed to load JSON:", e)
        sys.exit(1)

    fieldnames = [
        "job_id", "title", "description", "place", "address", "work_days",
        "start_time", "end_time", "participants", "client", "hourly_wage",
        "lat", "lng", "stamina_level"
    ]

    os.makedirs(out_path.parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        def detect_and_map_lat_lng(obj):
            # Attempt to map various lat/lng key names into canonical 'lat' and 'lng'.
            lat = None
            lng = None
            # direct keys
            for k in ("lat", "latitude"):
                if k in obj and obj.get(k) not in (None, ""):
                    try:
                        lat = float(obj.get(k))
                        break
                    except Exception:
                        pass
            for k in ("lng", "lon", "long", "longitude"):
                if k in obj and obj.get(k) not in (None, ""):
                    try:
                        lng = float(obj.get(k))
                        break
                    except Exception:
                        pass

            # ambiguous 'lang' key: could be language or mis-typed 'long'
            if (lat is None or lng is None) and "lang" in obj:
                v = obj.get("lang")
                try:
                    vf = float(v)
                    # decide by value range: lat in [-90,90], lng in [-180,180]
                    if -90.0 <= vf <= 90.0 and lat is None:
                        lat = vf
                    elif -180.0 <= vf <= 180.0 and lng is None:
                        # if value fits both ranges, prefer lng only if lat already present
                        if lat is not None:
                            lng = vf
                        else:
                            # ambiguous: if there is another numeric-looking field, attempt to place
                            lng = vf
                except Exception:
                    # non-numeric 'lang' — treat as language field, ignore for geo
                    pass

            return lat, lng

        for j in jobs:
            # normalize mapping from arbitrary JSON fields to canonical CSV columns
            row = {k: "" for k in fieldnames}
            # direct copy for common keys
            for key in ("job_id", "title", "description", "place", "address", "work_days",
                        "start_time", "end_time", "participants", "client", "hourly_wage"):
                if key in j:
                    row[key] = j.get(key) if j.get(key) is not None else ""

            # try to map latitude/longitude
            lat, lng = detect_and_map_lat_lng(j)
            if lat is None and "lat" in j:
                try:
                    lat = float(j.get("lat"))
                except Exception:
                    lat = None
            if lng is None and "lng" in j:
                try:
                    lng = float(j.get("lng"))
                except Exception:
                    lng = None

            row["lat"] = lat if lat is not None else ""
            row["lng"] = lng if lng is not None else ""

            # leave stamina_level blank so rebuild_embeddings.py (LLM-only) will compute it
            row["stamina_level"] = ""

            writer.writerow(row)

    print(f"Wrote CSV: {out_path}")

    # Embedding step (optional): perform LLM-only stamina classification and generate embeddings
    if not args.no_embed:
        CLOVA_LLM_API_KEY = os.getenv("CLOVA_LLM_API_KEY")
        CLOVA_LLM_URL = os.getenv("CLOVA_LLM_URL")

        # prepare embedding executor (lightweight copy of logic from rebuild_embeddings.py)
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

                    if data.get("status", {}).get("code") == "20000":
                        return data["result"].get("embedding", [])
                    elif data.get("status", {}).get("code") == "42901":
                        retry_after = int(res.getheader('X-RateLimit-Reset', 60))
                        print(f"Rate limit hit, sleeping {retry_after}s")
                        time.sleep(retry_after)
                        return self.get_embedding(text)
                    else:
                        print(f"[ERROR] Embedding API 오류: {data}")
                        return []
                except Exception as e:
                    print(f"[ERROR] Embedding 생성 실패: {e}")
                    return []

        def get_clova_embedding(text: str):
            if not CLOVA_LLM_API_KEY or not CLOVA_LLM_URL:
                print("[ERROR] CLOVA_LLM_API_KEY or CLOVA_LLM_URL not set. Embedding step requires these env vars.")
                sys.exit(1)
            exe = EmbeddingExecutor()
            return exe.get_embedding(text)

        # LLM-only stamina classifier (copied from rebuild_embeddings.py)
        def classify_stamina_with_llm(text: str) -> Optional[str]:
            if not CLOVA_LLM_API_KEY or not CLOVA_LLM_URL:
                print("[ERROR] CLOVA_LLM_API_KEY or CLOVA_LLM_URL not set. LLM-only mode requires these env vars.")
                sys.exit(1)
            try:
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

        # load CSV into DataFrame and run embedding loop
        df = pd.read_csv(out_path)
        print(f"Loaded {len(df)} rows for embedding step from {out_path}")

        success_count = 0
        fail_count = 0

        skip_existing = args.skip_existing and not args.force
        if args.clear_embeddings:
            print("--clear-embeddings specified: clearing existing embedding column values")
            df['embedding'] = ''

        for idx, row in df.iterrows():
            if skip_existing and str(row.get('embedding', '')).strip():
                print(f"[SKIP] Row {idx} already has embedding")
                continue

            # ensure stamina via LLM
            stamina = None
            if 'stamina_level' in row.index and str(row.get('stamina_level', '')).strip():
                stamina = row.get('stamina_level')
            else:
                text_for_class = " ".join([str(row.get(k, "")) for k in ['title', 'description', 'place', 'client']])
                stamina = classify_stamina_with_llm(text_for_class)
                if not stamina:
                    print(f"[ERROR] LLM failed to classify stamina for row {idx}. Aborting due to LLM-only policy.")
                    sys.exit(1)
                try:
                    df.at[idx, 'stamina_level'] = stamina
                except Exception:
                    df.loc[idx, 'stamina_level'] = stamina

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
            if not text_for_embedding.strip():
                print(f"[INFO] Row {idx} skipped (empty text)")
                fail_count += 1
                continue

            try:
                new_embedding = get_clova_embedding(text_for_embedding)
                if new_embedding and len(new_embedding) == 1024:
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

            if (idx + 1) % 10 == 0:
                time.sleep(1)

        # save final CSV
        try:
            df.to_csv(args.embed_output, index=False, encoding='utf-8-sig')
            print(f"\n=== ✅ 완료! ===")
            print(f"새 파일 저장: {args.embed_output}")
            print(f"성공: {success_count}개, 실패: {fail_count}개")
        except Exception as e:
            print(f"❌ 저장 실패: {e}")

if __name__ == "__main__":
    main()
