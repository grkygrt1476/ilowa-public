# ai_modeling/services/clova_llm.py
# -*- coding: utf-8 -*-
import os
import json
import re
import uuid
import requests
from dotenv import load_dotenv

load_dotenv()

CLOVA_LLM_API_KEY = os.getenv("CLOVA_LLM_API_KEY")
CLOVA_LLM_URL = os.getenv("CLOVA_LLM_URL")  # https://clovastudio.stream.ntruss.com

class CompletionExecutor:
    def __init__(self):
        self._host = CLOVA_LLM_URL
        self._api_key = f"Bearer {CLOVA_LLM_API_KEY}"
        self._request_id = str(uuid.uuid4())

    def execute(self, completion_request: dict):
        # Check if streaming is disabled
        stream_enabled = completion_request.get('stream', True)
        
        headers = {
            'Authorization': self._api_key,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
        }
        
        # Set headers based on streaming mode
        if stream_enabled:
            headers['Accept'] = 'text/event-stream'
        else:
            headers['Accept'] = 'application/json'
        
        # Remove stream parameter from request data before sending
        request_data = completion_request.copy()
        request_data.pop('stream', None)

        if stream_enabled:
            # Streaming mode
            with requests.post(
                self._host + '/v3/chat-completions/HCX-005',
                headers=headers, json=request_data, stream=True
            ) as r:
                # The endpoint streams SSE-like lines. Each meaningful payload is usually
                # sent as a `data: ...` line containing a JSON object. Naively concatenating
                # raw lines causes extraneous metadata to mix into the returned text which
                # breaks downstream JSON parsing. Here we extract and assemble only the
                # textual content pieces from the streamed JSON payloads.
                pieces = []
                for raw_line in r.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        decoded = raw_line.decode("utf-8").strip()
                    except Exception:
                        # fallback: try to coerce to str
                        decoded = str(raw_line)

                    # Lines may include `data: {...}` or other SSE fields. Extract payloads
                    # after `data:` if present. A single decoded line may contain multiple
                    # events separated by newlines, so split and handle each part.
                    for part in decoded.splitlines():
                        part = part.strip()
                        if not part:
                            continue
                        # Typical SSE payload prefix
                        if part.startswith('data:'):
                            payload = part[len('data:'):].strip()
                        else:
                            payload = part

                        # Skip stream end marker
                        if payload == '[DONE]':
                            continue

                        # Try to parse JSON payload and extract any text fields commonly
                        # used by the API. If parsing fails, use the raw payload as fallback.
                        extracted = None
                        try:
                            obj = json.loads(payload)
                            # Common shapes: {'message':{'content': ...}},
                            # {'delta': {'content': '...'}}, {'choices': [...]}, etc.
                            if isinstance(obj, dict):
                                # message -> content
                                if 'message' in obj and isinstance(obj['message'], dict):
                                    cont = obj['message'].get('content')
                                    if isinstance(cont, str):
                                        extracted = cont
                                    elif isinstance(cont, list):
                                        # content may be a list of {'type':'text','text':...}
                                        texts = []
                                        for c in cont:
                                            if isinstance(c, dict) and c.get('type') == 'text' and 'text' in c:
                                                texts.append(c['text'])
                                        if texts:
                                            extracted = ''.join(texts)

                                # delta style
                                if extracted is None and 'delta' in obj and isinstance(obj['delta'], dict):
                                    delta = obj['delta']
                                    if 'content' in delta and isinstance(delta['content'], str):
                                        extracted = delta['content']

                                # choices style (OpenAI-like)
                                if extracted is None and 'choices' in obj and isinstance(obj['choices'], list):
                                    texts = []
                                    for ch in obj['choices']:
                                        # delta.content
                                        if isinstance(ch, dict):
                                            if 'delta' in ch and isinstance(ch['delta'], dict):
                                                d = ch['delta'].get('content') or ch['delta'].get('text')
                                                if isinstance(d, str):
                                                    texts.append(d)
                                            # message.content
                                            if 'message' in ch and isinstance(ch['message'], dict):
                                                mcont = ch['message'].get('content')
                                                if isinstance(mcont, str):
                                                    texts.append(mcont)
                                    if texts:
                                        extracted = ''.join(texts)

                                # fallback: if object has a top-level 'text' field
                                if extracted is None and 'text' in obj and isinstance(obj['text'], str):
                                    extracted = obj['text']

                            # if not extracted, stringify payload
                        except Exception:
                            pass

                        if extracted is None:
                            # use raw payload when no structured text found
                            extracted = payload

                        # append extracted text fragment
                        if extracted:
                            pieces.append(extracted)

                # Join fragments into a single text response for backward compatibility.
                # Many downstream callers expect plain text (possibly including code
                # fences). Keep fragments contiguous without adding extra metadata.
                assembled = ''.join(pieces)

                # Post-process assembled stream: attempt to extract a JSON block inside
                # a ```json ... ``` fence (common in event:result). If found, clean
                # any inlined SSE metadata like `id:...event:...` that can corrupt JSON
                # (these tokens sometimes get interleaved into the stream) and return
                # the cleaned JSON string so callers can json.loads() it directly.
                try:
                    # prefer fenced JSON
                    m = re.search(r'```json\s*(\{.*?\})\s*```', assembled, re.DOTALL)
                    if not m:
                        # fallback: sometimes the event:result doesn't include fences
                        # but places the JSON directly after 'event:result'
                        m = re.search(r'event:result\s*(\{.*?\})\s*(?:event:signal|$)', assembled, re.DOTALL)

                    if m:
                        json_candidate = m.group(1)
                        # remove common injected metadata tokens that break JSON
                        json_candidate = re.sub(r'id:[0-9a-fA-F-]+event:\w+', '', json_candidate)
                        json_candidate = re.sub(r'event:\w+', '', json_candidate)
                        # remove stray id:... occurrences
                        json_candidate = re.sub(r'id:[0-9a-fA-F-]+', '', json_candidate)
                        # collapse repeated whitespace introduced by removals
                        json_candidate = re.sub(r'\s+', ' ', json_candidate).strip()
                        return json_candidate
                except Exception:
                    # if any regex/cleanup fails, fall back to the assembled text
                    pass

                return assembled
        else:
            # Non-streaming mode — try to request a single JSON response. If the
            # API rejects the non-streaming shape (400/5xx), fall back to streaming
            # and use the streaming assembler logic so clients remain robust.
            try:
                response = requests.post(
                    self._host + '/v3/chat-completions/HCX-005',
                    headers=headers, json=request_data
                )
                response.raise_for_status()
                result = response.json()
            except Exception as e:
                # Fallback: try streaming POST and reuse the streaming assembly
                with requests.post(
                    self._host + '/v3/chat-completions/HCX-005',
                    headers={**headers, 'Accept': 'text/event-stream'}, json=request_data, stream=True
                ) as r:
                    pieces = []
                    for raw_line in r.iter_lines():
                        if not raw_line:
                            continue
                        try:
                            decoded = raw_line.decode("utf-8").strip()
                        except Exception:
                            decoded = str(raw_line)
                        for part in decoded.splitlines():
                            part = part.strip()
                            if not part:
                                continue
                            if part.startswith('data:'):
                                payload = part[len('data:'):].strip()
                            else:
                                payload = part
                            if payload == '[DONE]':
                                continue
                            extracted = None
                            try:
                                obj = json.loads(payload)
                                if isinstance(obj, dict):
                                    if 'message' in obj and isinstance(obj['message'], dict):
                                        cont = obj['message'].get('content')
                                        if isinstance(cont, str):
                                            extracted = cont
                                        elif isinstance(cont, list):
                                            texts = []
                                            for c in cont:
                                                if isinstance(c, dict) and c.get('type') == 'text' and 'text' in c:
                                                    texts.append(c['text'])
                                            if texts:
                                                extracted = ''.join(texts)
                                    if extracted is None and 'delta' in obj and isinstance(obj['delta'], dict):
                                        delta = obj['delta']
                                        if 'content' in delta and isinstance(delta['content'], str):
                                            extracted = delta['content']
                                    if extracted is None and 'choices' in obj and isinstance(obj['choices'], list):
                                        texts = []
                                        for ch in obj['choices']:
                                            if isinstance(ch, dict):
                                                if 'delta' in ch and isinstance(ch['delta'], dict):
                                                    d = ch['delta'].get('content') or ch['delta'].get('text')
                                                    if isinstance(d, str):
                                                        texts.append(d)
                                                if 'message' in ch and isinstance(ch['message'], dict):
                                                    mcont = ch['message'].get('content')
                                                    if isinstance(mcont, str):
                                                        texts.append(mcont)
                                        if texts:
                                            extracted = ''.join(texts)
                                    if extracted is None and 'text' in obj and isinstance(obj['text'], str):
                                        extracted = obj['text']
                            except Exception:
                                pass
                            if extracted is None:
                                extracted = payload
                            if extracted:
                                pieces.append(extracted)

                    assembled = ''.join(pieces)
                    # Try to extract fenced JSON
                    m = re.search(r'```json\s*(\{.*?\})\s*```', assembled, re.DOTALL)
                    if not m:
                        m = re.search(r'event:result\s*(\{.*?\})\s*(?:event:signal|$)', assembled, re.DOTALL)
                    if m:
                        jc = m.group(1)
                        jc = re.sub(r'id:[0-9a-fA-F-]+event:\w+', '', jc)
                        jc = re.sub(r'event:\w+', '', jc)
                        jc = re.sub(r'id:[0-9a-fA-F-]+', '', jc)
                        jc = re.sub(r'\s+', ' ', jc).strip()
                        return jc
                    return assembled
            # Try to handle different non-stream response shapes.
            # 1) OpenAI-like: { 'choices': [ { 'message': { 'content': '...' } } ] }
            if 'choices' in result and isinstance(result['choices'], list) and len(result['choices']) > 0:
                choice = result['choices'][0]
                if isinstance(choice, dict):
                    # message.content
                    msg = choice.get('message')
                    if isinstance(msg, dict) and 'content' in msg:
                        content = msg['content']
                        # if content wrapped in code fence and contains JSON, extract it
                        m = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                        if m:
                            return m.group(1)
                        return content
                    # older shape: text
                    if 'text' in choice:
                        return choice['text']

            # 2) ClovaStudio-like: { 'status': {...}, 'result': { 'message': { 'content': '...' }, ... } }
            if 'result' in result and isinstance(result['result'], dict):
                msg = result['result'].get('message')
                if isinstance(msg, dict) and 'content' in msg:
                    content = msg['content']
                    # content may be a string or list; normalize
                    if isinstance(content, list):
                        # extract text items
                        texts = []
                        for c in content:
                            if isinstance(c, dict) and c.get('type') == 'text' and 'text' in c:
                                texts.append(c['text'])
                        content = ''.join(texts)

                    if isinstance(content, str):
                        # If there's a fenced JSON block, extract and clean it
                        m = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                        if not m:
                            m = re.search(r'event:result\s*(\{.*?\})\s*(?:event:signal|$)', content, re.DOTALL)
                        if m:
                            jc = m.group(1)
                            jc = re.sub(r'id:[0-9a-fA-F-]+event:\w+', '', jc)
                            jc = re.sub(r'event:\w+', '', jc)
                            jc = re.sub(r'id:[0-9a-fA-F-]+', '', jc)
                            jc = re.sub(r'\s+', ' ', jc).strip()
                            return jc
                        return content

            # Fallback: return stringified JSON response
            return json.dumps(result, ensure_ascii=False)

def refine_with_clova_llm(parsed: dict) -> dict:
    """
    OCR + HTML 파싱 결과 parsed dict를 LLM에 보내 JSON 스키마로 정제
    """
    schema = {
        "title": "",
        "participants": 0,
        "hourly_wage": 0,
        "place": "",
        "address": "",
        "work_days": "",
        "start_time": "",
        "end_time": "",
        "client": "",
        "description": ""
    }

    if not CLOVA_LLM_API_KEY or not CLOVA_LLM_URL:
        # 환경변수 없으면 fallback
        out = dict(schema)
        out.update({
            "title": parsed.get("title") or parsed.get("raw_text","")[:60],
            "participants": parsed.get("participants", 0),
            "hourly_wage": parsed.get("hourly_wage", 0),
            "place": parsed.get("place") or parsed.get("address",""),
            "address": parsed.get("address",""),
            "work_days": parsed.get("work_days","1111111"),
            "start_time": parsed.get("start_time","09:00:00"),
            "end_time": parsed.get("end_time","18:00:00"),
            "client": parsed.get("client","미상"),
            "description": parsed.get("description", parsed.get("raw_text","")[:200])
        })
        return out

    # Build prompt
    prompt = f"""
아래는 OCR로 추출한 소일거리 공고의 임시 파싱 결과입니다.
이를 다음 JSON 스키마에 맞추어 정제해서 출력하세요. **반드시 JSON만** 출력하세요.

스키마:
{json.dumps(schema, ensure_ascii=False, indent=2)}

파싱결과:
{json.dumps(parsed, ensure_ascii=False, indent=2)}

주의:
- 금액/인원은 숫자(정수)로.
- 누락된 값은 가능한 한 raw_text에서 추론해서 채우되, 불확실하면 기본값(0/미상 등)을 사용.
"""
    executor = CompletionExecutor()
    request_data = {
        "messages": [
            {"role": "system", "content":[{"type":"text","text":"소일거리 공고 정제"}]},
            {"role": "user", "content":[{"type":"text","text": prompt}]}
        ],
        "topP": 0.8,
        "topK": 0,
        "maxTokens": 800,
        "temperature": 0.0,
        "repetitionPenalty": 1.1,
        "stop": []
    }

    try:
        response_text = executor.execute(request_data)
    except Exception as exc:
        # Network / request failure (DNS, timeout, etc.) -> fallback to local heuristic
        # Avoid bubbling up to FastAPI as 500 so the API remains testable offline/dev.
        # We intentionally do not re-raise here.
        # Optionally log the exception to stderr
        try:
            import traceback
            traceback.print_exc()
        except Exception:
            pass
        out = dict(schema)
        out.update({
            "title": parsed.get("title") or parsed.get("raw_text", "")[:60],
            "participants": parsed.get("participants", 0),
            "hourly_wage": parsed.get("hourly_wage", 0),
            "place": parsed.get("place") or parsed.get("address", ""),
            "address": parsed.get("address", ""),
            "work_days": parsed.get("work_days", "1111111"),
            "start_time": parsed.get("start_time", "09:00:00"),
            "end_time": parsed.get("end_time", "18:00:00"),
            "client": parsed.get("client", "미상"),
            "description": parsed.get("description", parsed.get("raw_text", "")[:200])
        })
        return out

    # JSON 파싱 시도
    try:
        parsed_json = json.loads(response_text)
        return parsed_json
    except Exception:
        # 실패하면 최소 fallback
        out = dict(schema)
        out.update({
            "title": parsed.get("title") or response_text[:60],
            "participants": parsed.get("participants", 0),
            "hourly_wage": parsed.get("hourly_wage", 0),
            "place": parsed.get("place") or parsed.get("address", ""),
            "address": parsed.get("address", ""),
            "work_days": parsed.get("work_days", "1111111"),
            "start_time": parsed.get("start_time", "09:00:00"),
            "end_time": parsed.get("end_time", "18:00:00"),
            "client": parsed.get("client", "미상"),
            "description": parsed.get("description", parsed.get("raw_text", "")[:200])
        })
        return out