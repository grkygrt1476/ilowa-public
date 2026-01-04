# -*- coding: utf-8 -*-
import os
import json
import uuid
import http.client
from dotenv import load_dotenv

load_dotenv()

# NCP 가이드에 따라 환경변수에서 불러오기
CLOVA_LLM_API_KEY = os.getenv("CLOVA_LLM_API_KEY")
CLOVA_LLM_URL = os.getenv("CLOVA_LLM_URL")  # https://clovastudio.stream.ntruss.com

# host는 URL에서 도메인만 추출
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

        conn = http.client.HTTPSConnection(self._host)
        conn.request('POST', REQUEST_PATH, json.dumps(payload), headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        conn.close()

        if data.get("status", {}).get("code") == "20000":
            return data["result"].get("embedding", [])
        else:
            return []

# ★ 새로 추가: 간단한 함수 형태 래퍼
_executor = EmbeddingExecutor()
def get_clova_embedding(text: str):
    return _executor.get_embedding(text)