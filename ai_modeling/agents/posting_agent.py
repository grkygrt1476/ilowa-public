#ai_modeling/agents/posting_agent.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
import re
import json
from ai_modeling.services.html_parser import parse_html_to_structured
from ai_modeling.services.providers import AIProvider, get_ai_provider

class PostingAutomationAgent:
    """
    Voice/Image/Text -> Structured Job Post extractor using LLM for all judgments.
    """

    RAW_TEXT_MAX_LEN = 2000
    def __init__(self, provider: AIProvider | None = None):
        self.provider = provider or get_ai_provider()
        self.provider_name = getattr(self.provider, "name", "unknown")

    def extract_from_input(self, input_data: Any, input_type: str) -> Dict[str, Any]:
        """
        Unified extraction method using LLM for all input types.
        input_type: 'voice' (file_path), 'image' (bytes), 'text' (str)
        """
        schema = {
            "title": "",
            "category": "",
            "region": "",
            "address": "",
            "schedule_days": [],
            "time_slots": [],
            "start_time": "",
            "end_time": "",
            "frequency": "",
            "participants": 0,
            "wage_type": "hourly",
            "hourly_wage": 0,
            "wage_amount": "",
            "qualifications": [],
            "description": "",
            "raw_text": "",
            "confidence": {}
        }

        transcript_text = None

        # Prepare input text based on type
        if input_type == "voice":
            stt = self.provider.transcribe_audio(input_data, lang="Kor")
            text = stt.get("text", "").strip()
            if not text:
                return {"success": False, "message": "음성 인식 실패", "post": {}}
            polished = self._polish_transcript_text(text)
            final_text = polished or text
            input_description = f"음성 입력: {final_text}"
            transcript_text = final_text
            text = final_text
        elif input_type == "image":
            html = self.provider.ocr_image(input_data)
            parsed = parse_html_to_structured(html)
            
            # Let LLM handle all the parsing - pass raw HTML and structured data
            text = f"""
원본 HTML: {html}
구조화된 데이터: {parsed}
추출된 텍스트: {parsed.get('text', '') or parsed.get('raw_text', '')}
테이블 데이터: {parsed.get('tables', [])}
"""
            input_description = f"이미지 OCR 결과: {text}"
        elif input_type == "text":
            text = input_data
            input_description = f"텍스트 입력: {text}"
        else:
            return {"success": False, "message": "지원하지 않는 입력 타입", "post": {}}

        prompt = f"""
아래 입력으로부터 구인 공고 정보를 구조화합니다.

[중요] 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트, 설명, 코드블록, 마크다운을 절대 추가하지 마세요.
JSON 시작과 끝 외에 어떤 문자도 출력하지 마세요.

{{
    "title": "공고 제목",
    "category": "카테고리",
    "region": "지역",
    "address": "상세 주소",
    "schedule_days": ["요일1", "요일2"],
    "time_slots": ["시간대"],
    "start_time": "시작시간",
    "end_time": "종료시간",
    "frequency": "빈도",
    "participants": 숫자,
    "wage_type": "hourly",
    "hourly_wage": 숫자,
    "wage_amount": "급여설명",
    "qualifications": ["자격요건1", "자격요건2"],
    "description": "자세한 설명",
    "raw_text": "",
    "confidence": {{}}
}}

규칙:
- 모든 값은 한국어로 작성
- schedule_days: "월요일에서 금요일까지" → ["월요일", "화요일", "수요일", "목요일", "금요일"]
- time_slots: "오후" 등 시간대 추출
- start_time/end_time: "14:00:00" 형식으로 변환
- participants: 숫자로 변환 (예: "한 명" → 1)
- hourly_wage: 숫자로 변환 (예: "15000원" → 15000)
- 숫자 필드에서 계산식(예: 761040/60)은 금지, 반드시 계산된 숫자만 기재
- 빈 값은 빈 문자열 "" 또는 빈 배열 [] 사용
- raw_text 값은 항상 빈 문자열 "" 로 두세요 (시스템이 자동으로 채웁니다)

입력:
{input_description}
"""

        # Use Clova-style structured messages and low-temperature deterministic settings
        completion_request = {
            "messages": [
                {"role": "system", "content": [{"type": "text", "text": (
                    "You are a JSON-only extractor.\n"
                    "Return exactly one JSON object that matches the schema provided.\n"
                    "Do NOT include any explanations, markdown, code fences, or extra text.\n"
                    "If a field cannot be determined, return an empty string, 0, or [] as appropriate."
                )}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            # Clova expects maxTokens / temperature; avoid unsupported params like topP/topK
            "maxTokens": 1000,
            "temperature": 0.0,
            "stream": False
        }

        raw_text_snippet = (text or "")[:self.RAW_TEXT_MAX_LEN]

        def attach_success(structured_data: Dict[str, Any]) -> Dict[str, Any]:
            structured_data["raw_text"] = raw_text_snippet
            result: Dict[str, Any] = {"success": True, "post": structured_data}
            if transcript_text is not None:
                result["transcript"] = transcript_text
            return result

        response = self.provider.generate_completion(completion_request)
        response = self._normalize_llm_response(response)

        # Parse the JSON response - should be pure JSON now. If parsing fails,
        # try several progressively aggressive recovery strategies.
        def try_load(s: str):
            return json.loads(s)

        # 1) Direct parse - only accept if it looks like our schema (has 'title')
        try:
            structured_data = try_load(response.strip())
            if isinstance(structured_data, dict) and 'title' in structured_data:
                return attach_success(structured_data)
        except Exception:
            pass

        # Debug print for the raw response (helpful during development)
        print("LLM 응답 디버깅 (원본):", repr(response))

        def _cleanup_candidate(candidate: str) -> str:
            candidate = re.sub(r'id:[0-9a-fA-F-]+event:\w+', '', candidate)
            candidate = re.sub(r'event:\w+', '', candidate)
            candidate = re.sub(r'id:[0-9a-fA-F-]+', '', candidate)
            return candidate.strip()

        # 2) Extract fenced ```json ... ``` block (allow missing closing fence)
        for pattern in [
            r'```json\s*(\{.*?\})\s*```',
            r'```json\s*(\{.*)',  # closing ``` omitted
        ]:
            try:
                m = re.search(pattern, response, re.DOTALL)
                if m:
                    candidate = _cleanup_candidate(m.group(1))
                    structured_data = try_load(candidate)
                    if isinstance(structured_data, dict) and 'title' in structured_data:
                        return attach_success(structured_data)
            except Exception:
                pass

        # 3) Extract JSON following event:result ... event:signal
        try:
            m = re.search(r'event:result\s*(\{.*?\})\s*(?:event:signal|$)', response, re.DOTALL)
            if m:
                candidate = _cleanup_candidate(m.group(1))
                structured_data = try_load(candidate)
                if isinstance(structured_data, dict) and 'title' in structured_data:
                    return attach_success(structured_data)
        except Exception:
            pass

        # 4) Heuristic: take from first '{' to last '}' and try to parse
        try:
            first = response.find('{')
            last = response.rfind('}')
            if first != -1 and last != -1 and last > first:
                candidate = _cleanup_candidate(response[first:last+1])
                structured_data = try_load(candidate)
                if isinstance(structured_data, dict) and 'title' in structured_data:
                    return attach_success(structured_data)
        except Exception:
            pass

        # 5) Remove code fences entirely and retry once more
        try:
            fence_stripped = response.replace("```json", "").replace("```", "").strip()
            first = fence_stripped.find('{')
            last = fence_stripped.rfind('}')
            if first != -1 and last != -1 and last > first:
                candidate = _cleanup_candidate(fence_stripped[first:last+1])
                structured_data = try_load(candidate)
                if isinstance(structured_data, dict) and 'title' in structured_data:
                    return attach_success(structured_data)
        except Exception:
            pass

        # If all recovery attempts fail, include the cleaned candidate snippets in the debug
        cleaned = re.sub(r'id:[0-9a-fA-F-]+event:\w+', '', response)
        cleaned = re.sub(r'event:\w+', '', cleaned)
        cleaned = re.sub(r'id:[0-9a-fA-F-]+', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        print("LLM 응답 디버깅 (정리):", repr(cleaned))
        raise ValueError("LLM 응답이 유효한 JSON이 아닙니다. 디버그 로그를 확인하세요.")

    def extract_from_voice(self, file_path: str) -> Dict[str, Any]:
        return self.extract_from_input(file_path, "voice")

    def extract_from_image_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        return self.extract_from_input(image_bytes, "image")

    def extract_from_text(self, text: str) -> Dict[str, Any]:
        return self.extract_from_input(text, "text")

    def _append_raw_text(self, existing: str, addition: str) -> str:
        """Append text while keeping overall length bounded."""
        base = (existing or "").strip()
        extra = (addition or "").strip()
        if base and extra:
            combined = f"{base}\n{extra}"
        elif extra:
            combined = extra
        else:
            combined = base
        if len(combined) > self.RAW_TEXT_MAX_LEN:
            return combined[-self.RAW_TEXT_MAX_LEN :]
        return combined

    def _normalize_llm_response(self, response: str) -> str:
        """Normalize minor numeric expressions (e.g., 761040/60) into numbers."""
        def repl(match: re.Match[str]) -> str:
            numerator = int(match.group(1))
            denominator = int(match.group(2)) or 1
            value = numerator / denominator
            if value.is_integer():
                value = int(value)
            return f": {value}"

        return re.sub(r":\s*([0-9]+)\s*/\s*([0-9]+)", repl, response)

    def _polish_transcript_text(self, text: str) -> str:
        """
        Clean up STT output to fix spacing and obvious typos using the provider LLM.
        Returns the original text if polishing fails.
        """
        cleaned = (text or "").strip()
        if not cleaned:
            return ""

        prompt = (
            "다음 음성 인식 결과 문장을 자연스러운 한국어로 맞춤법과 띄어쓰기를 교정해 주세요.\n"
            "뜻은 변경하지 말고, 결과만 한 문단의 텍스트로 출력하세요.\n\n"
            f"{cleaned}\n\n"
            "교정된 문장:"
        )

        request = {
            "messages": [
                {"role": "system", "content": [{"type": "text", "text": (
                    "You are a Korean proofreader who fixes spacing and spelling without changing meaning."
                )}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            "maxTokens": 400,
            "temperature": 0.0,
            "stream": False
        }

        try:
            response = self.provider.generate_completion(request)
            normalized = (response or "").strip()
            normalized = re.sub(r"^교정된 문장[:：]\s*", "", normalized, flags=re.IGNORECASE)
            if normalized.startswith(("\"", "“")) and normalized.endswith(("\"", "”")) and len(normalized) > 1:
                normalized = normalized[1:-1].strip()
            return normalized or cleaned
        except Exception:
            return cleaned

    def normalize_address(self, address_text: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Use the LLM to rewrite fuzzy addresses into a geocodable format."""
        raw = (address_text or "").strip()
        if not raw:
            return None

        context_lines: list[str] = []
        if context:
            for key in ("region", "place", "location", "description"):
                value = context.get(key)
                if value and isinstance(value, str):
                    context_lines.append(f"{key}: {value.strip()}")
        context_snippet = "\n".join(context_lines[:4])

        prompt = f"""
다음 위치 설명을 기반으로 구글 지도에서 검색 가능한 행정 주소(도로명 주소 또는 지번 주소)를 한 문장으로 작성해주세요.
가능하다면 대한민국 주소 체계를 따라 시/구/동/번지를 포함해주세요.
입력: {raw}
추가 정보:
{context_snippet or "없음"}

반환 형식:
- 주소만 한 줄로 작성 (예: "서울특별시 중구 다산로32길 22").
- 다른 설명이나 따옴표를 붙이지 마세요.
"""

        request = {
            "messages": [
                {"role": "system", "content": [{"type": "text", "text": (
                    "You rewrite rough Korean location descriptions into precise postal addresses."
                )}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            "maxTokens": 200,
            "temperature": 0.0,
            "stream": False
        }

        try:
            response = self.provider.generate_completion(request)
            normalized = (response or "").strip()
            normalized = normalized.replace("주소:", "").replace("주소 :", "").strip()
            if normalized.startswith(("\"", "“")) and normalized.endswith(("\"", "”")) and len(normalized) > 1:
                normalized = normalized[1:-1].strip()
            normalized = normalized.replace("\n", " ").strip()
            return normalized or raw
        except Exception:
            return raw

    def check_missing_fields(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for missing or empty important fields and return a structure
        used by the router to decide whether clarification is needed.

        Returns:
          { needs_clarification: bool,
            missing_fields: List[str],
            questions: List[str] }
        """
        required = [
            "title",
            "region",
            "schedule_days",
            "start_time",
            "participants",
            "hourly_wage",
            "description",
        ]
        
        missing = []
        questions = []
        # simple emptiness checks
        for f in required:
            val = post.get(f)
            empty = False
            if val is None:
                empty = True
            elif isinstance(val, str) and val.strip() == "":
                empty = True
            elif isinstance(val, (list, dict)) and len(val) == 0:
                empty = True
            elif isinstance(val, (int, float)) and val == 0:
                # wage or participants could be 0 meaning missing
                if f in ("participants", "hourly_wage"):
                    empty = True

            if empty:
                missing.append(f)
                # generate a simple Korean question for each field
                if f == "title":
                    questions.append("공고 제목을 알려주시겠어요?")
                elif f == "region":
                    questions.append("어느 지역에서 근무하시나요? (예: 서울 송파구)")
                elif f == "schedule_days":
                    questions.append("근무 가능한 요일을 알려주세요. (예: 월~금 또는 월,수,금)")
                elif f == "start_time":
                    questions.append("근무 시작 시간을 알려주세요. (예: 오전 9시 -> 09:00)")
                elif f == "participants":
                    questions.append("몇 명을 모집하시나요?")
                elif f == "hourly_wage":
                    questions.append("희망 시급을 알려주세요. (예: 15000원)")
                elif f == "description":
                    questions.append("공고에 들어갈 자세한 설명을 추가로 해주세요.")

        # confidence map to record any inferred values
        confidence_map = post.get("confidence", {}) or {}

        # If there are missing fields, attempt lightweight inference before asking the user.
        # 1) Heuristic fills from raw_text/description
        if len(missing) > 0:
            rt = (post.get("raw_text") or "") + "\n" + (post.get("description") or "")
            # title heuristics
            if "title" in missing:
                if "산책" in rt or "산책" in (post.get("description") or ""):
                    post["title"] = "반려동물 산책 도우미"
                    confidence_map["title"] = 0.6
                    missing.remove("title")
            # schedule_days heuristics: if text contains '하루' but no specific 요일, do not assume days
            # start_time heuristics: look for time expressions like '오전 9시', '9시'
            if "start_time" in missing:
                m = re.search(r"(오전|오후)?\s*(\d{1,2})시", rt)
                if m:
                    meridiem = m.group(1) or ""
                    hour = int(m.group(2))
                    if meridiem == "오후" and hour < 12:
                        hour += 12
                    post["start_time"] = f"{hour:02d}:00:00"
                    confidence_map["start_time"] = 0.7
                    missing.remove("start_time")
            # hourly_wage heuristics
            if "hourly_wage" in missing:
                m = re.search(r"(\d{3,6})\s*원", rt)
                if m:
                    try:
                        post["hourly_wage"] = int(m.group(1))
                        post["wage_amount"] = f"{m.group(1)}원"
                        confidence_map["hourly_wage"] = 0.7
                        missing.remove("hourly_wage")
                    except Exception:
                        pass

        # 2) If still missing and LLM is available, ask LLM to infer values with confidence scores.
        if len(missing) > 0:
            try:
                # Build a compact prompt instructing the LLM to infer only missing fields
                to_infer = {k: post.get(k) for k in missing}
                prompt = (
                    "다음은 이미 추출된 공고 데이터와 원문입니다. 누락된 필드에 대해 가능한 한 추론해 주십시오."
                    " 반드시 JSON 객체로만 응답하세요. 반환 형식은 {\"field\": {\"value\": ..., \"confidence\": 0.0}} 입니다."
                    " confidence는 0.0~1.0 사이 실수로, 0.6 이상이면 신뢰 가능한 값으로 간주합니다.\n\n"
                    f"원문:\n{(post.get('raw_text') or '')}\n설명:\n{(post.get('description') or '')}\n현재 누락 필드:\n{json.dumps(to_infer, ensure_ascii=False)}"
                )

                request = {
                    "messages": [
                        {"role": "system", "content": [{"type": "text", "text": (
                            "You are an assistant that infers missing JSON fields from given text."
                        )}]},
                        {"role": "user", "content": [{"type": "text", "text": prompt}]}
                    ],
                    "maxTokens": 400,
                    "temperature": 0.0,
                    "stream": False
                }

                inferred_text = self.provider.generate_completion(request)
                # parse LLM response
                inferred = None
                try:
                    inferred = json.loads(inferred_text)
                except Exception:
                    # try fenced JSON
                    m = re.search(r'```json\s*(\{.*?\})\s*```', inferred_text, re.DOTALL)
                    if m:
                        try:
                            inferred = json.loads(m.group(1))
                        except Exception:
                            inferred = None

                if isinstance(inferred, dict):
                    for field, info in inferred.items():
                        if field in missing and isinstance(info, dict):
                            val = info.get("value")
                            conf = info.get("confidence", 0)
                            try:
                                conf = float(conf)
                            except Exception:
                                conf = 0
                            if conf >= 0.6 and val not in (None, "", [], {}):
                                post[field] = val
                                confidence_map[field] = conf
                    # recompute missing/questions
                    new_missing = []
                    new_questions = []
                    for f in ["title","region","schedule_days","start_time","participants","hourly_wage","description"]:
                        v = post.get(f)
                        is_empty = (v is None or (isinstance(v,str) and v.strip()=="") or (isinstance(v,(list,dict)) and len(v)==0) or (isinstance(v,(int,float)) and v==0 and f in ("participants","hourly_wage")))
                        if is_empty:
                            new_missing.append(f)
                            # same question mapping as before
                            if f == "title":
                                new_questions.append("공고 제목을 알려주시겠어요?")
                            elif f == "region":
                                new_questions.append("어느 지역에서 근무하시나요? (예: 서울 송파구)")
                            elif f == "schedule_days":
                                new_questions.append("근무 가능한 요일을 알려주세요. (예: 월~금 또는 월,수,금)")
                            elif f == "start_time":
                                new_questions.append("근무 시작 시간을 알려주세요. (예: 오전 9시 -> 09:00)")
                            elif f == "participants":
                                new_questions.append("몇 명을 모집하시나요?")
                            elif f == "hourly_wage":
                                new_questions.append("희망 시급을 알려주세요. (예: 15000원)")
                            elif f == "description":
                                new_questions.append("공고에 들어갈 자세한 설명을 추가로 해주세요.")
                    missing = new_missing
                    questions = new_questions
            except Exception:
                # if LLM inference fails, silently continue and ask original questions
                pass

        # attach confidence map back to post for caller visibility
        post["confidence"] = confidence_map

        return {
            "needs_clarification": len(missing) > 0,
            "missing_fields": missing,
            "questions": questions,
        }

    def merge_additional_input(self, post: Dict[str, Any], additional_text: str) -> Dict[str, Any]:
        """
        Merge additional natural language input into an existing post dict.

        Primary attempt: ask the LLM to merge and return a full JSON object matching
        the schema. If LLM fails, perform a lightweight heuristic merge.
        """
        # Build a small prompt describing the current post and the new text
        prompt = f"""
아래는 이미 생성된 공고의 현재 상태입니다. 일부 필드가 비어있습니다.
이제 추가 음성에서 추출한 텍스트를 사용해 누락된 필드를 채워주세요.
반환값은 반드시 JSON 객체(스키마는 아래와 같음) 하나만 출력하세요. 다른 텍스트를 포함하지 마세요.

스키마:
{{
    "title": "",
    "category": "",
    "region": "",
    "address": "",
    "schedule_days": [],
    "time_slots": [],
    "start_time": "",
    "end_time": "",
    "frequency": "",
    "participants": 0,
    "wage_type": "hourly",
    "hourly_wage": 0,
    "wage_amount": "",
    "qualifications": [],
    "description": "",
    "raw_text": "",
    "confidence": {{}}
}}

현재 공고:
{json.dumps(post, ensure_ascii=False, indent=2)}

추가 텍스트:
{additional_text}

주의: 가능한 한 기존 값을 유지하고, 추가 텍스트에서 확실히 알 수 있는 값만 덮어쓰세요.
"""

        request = {
            "messages": [
                {"role": "system", "content": [{"type": "text", "text": (
                    "You are a JSON merger. Merge additional user text into the existing JSON post."
                )}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            "maxTokens": 800,
            "temperature": 0.0,
            "stream": False
        }

        try:
            merged_text = self.provider.generate_completion(request)
            try:
                merged = json.loads(merged_text)
                # Ensure raw_text contains concatenated inputs for traceability
                merged["raw_text"] = self._append_raw_text(post.get("raw_text", ""), additional_text)
                return merged
            except Exception:
                # If LLM returned non-JSON, fall through to heuristic
                pass
        except Exception:
            # LLM call failed; fallback to heuristics
            pass

        # Heuristic fallback: copy existing and try to extract a few fields from text
        out = dict(post)
        out.setdefault("raw_text", "")
        out["raw_text"] = self._append_raw_text(out.get("raw_text", ""), additional_text)

        # try to extract wage
        m = re.search(r"(\d{3,6})\s*원", additional_text)
        if m and (not out.get("hourly_wage") or out.get("hourly_wage") == 0):
            try:
                out["hourly_wage"] = int(m.group(1))
                out["wage_amount"] = f"{m.group(1)}원"
            except Exception:
                pass

        # participants
        m = re.search(r"(\d+)\s*명", additional_text)
        if m and (not out.get("participants") or out.get("participants") == 0):
            try:
                out["participants"] = int(m.group(1))
            except Exception:
                pass

        # schedule days (월~금, 월,수,금 등)
        weekdays = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
        range_m = re.search(r"([월화수목금토일])\s*~\s*([월화수목금토일])", additional_text)
        if range_m and (not out.get("schedule_days")):
            start = range_m.group(1)
            end = range_m.group(2)
            # map 한글 short to full
            short = {"월":"월요일","화":"화요일","수":"수요일","목":"목요일","금":"금요일","토":"토요일","일":"일요일"}
            try:
                si = weekdays.index(short[start])
                ei = weekdays.index(short[end])
                out["schedule_days"] = weekdays[si:ei+1]
            except Exception:
                pass
        else:
            # comma separated days
            found = [d for d in weekdays if d in additional_text]
            if found and (not out.get("schedule_days")):
                out["schedule_days"] = found

        return out
