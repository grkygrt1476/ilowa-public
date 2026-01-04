#!/usr/bin/env python3
"""
Offline-friendly demo for screenshotting an initial, schema-less LLM call using the OCR sample image.
기본은 로컬에서만 출력하고, --live를 주면 .env의 Clova 키/URL로 실제 LLM을 한 번 호출한다.
"""

import argparse
import json
import os
import re
import textwrap
import time
import uuid
import base64
from pathlib import Path
from typing import Any, Dict

import requests


def _load_env():
    """Load .env if python-dotenv is installed; otherwise do a minimal parse."""
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        load_dotenv = None

    if load_dotenv:
        load_dotenv()
        return

    env_path = Path(".env")
    if env_path.exists():
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val


_load_env()


DEFAULT_IMAGE = Path("ai_modeling/sample/test_post.png")


def _find_balanced_json(text: str) -> str | None:
    """
    문자열에서 첫 번째로 닫히는 { ... } JSON 오브젝트 부분 문자열을 찾아 반환한다.
    따옴표 내부와 이스케이프를 고려한 간단한 균형 검사.
    """
    start = None
    depth = 0
    in_string = False
    escape = False
    for idx, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    return text[start : idx + 1]
    return None



def fmt_size(path: Path) -> str:
    try:
        size = os.path.getsize(path)
    except OSError:
        return "size: unknown"
    units = ["B", "KB", "MB", "GB"]
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024.0
        idx += 1
    return f"size: {size:.1f}{units[idx]}"


def build_prompts(text: str) -> tuple[str, str]:
    """Return (printable_prompt, llm_prompt_with_text)."""
    printable = textwrap.dedent(
        """
        OCR 인식된 전단지 내용을 단 하나의 JSON 오브젝트로 정리해줘.
        반드시 아래 키만 포함할 것: ["title","place","work_days","time","hourly_wage","description","raw_text"].
        - raw_text에는 OCR 원문 전체를 그대로 넣고, 다른 필드에는 원문을 덧붙이지 말 것.
        - 없는 값은 null 또는 빈 문자열로 두고, 추가 키나 설명 텍스트를 넣지 말 것.
        - 숫자는 숫자로, 그 외는 문자열로 반환.
        """
    ).strip()
    llm_prompt = textwrap.dedent(
        f"""
        OCR 인식된 전단지 내용을 단 하나의 JSON 오브젝트로 정리해줘.
        반드시 아래 키만 포함할 것: ["title","place","work_days","time","hourly_wage","description","raw_text"].
        - raw_text에는 OCR 원문 전체를 그대로 넣고, 다른 필드에는 원문을 덧붙이지 말 것.
        - 없는 값은 null 또는 빈 문자열로 두고, 추가 키나 설명 텍스트를 넣지 말 것.
        - 숫자는 숫자로, 그 외는 문자열로 반환.

        OCR 원문:
        {text}
        """
    ).strip()
    return printable, llm_prompt


def build_example_llm_reply(text: str) -> Dict[str, Any]:
    """Derive a pseudo LLM reply from the OCR text for screenshot/offline use."""
    return {
        "title": "장애인시설도우미",
        "place": "송파시니어클럽",
        "work_days": "주5회",            # 예시: 문자열
        "time": "주 5회, 일 3시간",
        "hourly_wage": 761040,
        "description": text[:280] + ("..." if len(text) > 280 else ""),
        "raw_text": text,
    }


def call_clova_ocr(image_path: Path) -> str | None:
    """Call Clova OCR and return concatenated text, or None on failure."""
    url = os.getenv("CLOVA_OCR_URL")
    secret = os.getenv("CLOVA_OCR_SECRET")
    if not url or not secret:
        missing = []
        if not url:
            missing.append("CLOVA_OCR_URL")
        if not secret:
            missing.append("CLOVA_OCR_SECRET")
        print(f"[ocr] Missing env: {', '.join(missing)}. Using fallback text.")
        return None

    payload = {
        "images": [
            {
                "format": image_path.suffix.lstrip(".") or "png",
                "name": image_path.name,
                "data": base64.b64encode(image_path.read_bytes()).decode("utf-8"),
            }
        ],
        "lang": "ko",
        "requestId": str(uuid.uuid4()),
        "version": "V2",
        "timestamp": int(time.time() * 1000),
    }
    headers = {
        "X-OCR-SECRET": secret,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Clova OCR V2: data['images'][0]['fields'][*]['inferText']
        texts = []
        for img in data.get("images", []):
            for field in img.get("fields", []):
                text = field.get("inferText")
                if isinstance(text, str):
                    texts.append(text)
        if texts:
            return "\n".join(texts)
        return None
    except Exception as exc:
        print(f"[ocr] Clova OCR call failed: {exc}. Using fallback text.")
        return None


def call_clova_llm(prompt: str, model: str = "HCX-005") -> tuple[dict | None, str | None]:
    """Call Clova Studio chat-completions once. Returns (json, error_message)."""
    api_key = os.getenv("CLOVA_LLM_API_KEY")
    host = os.getenv("CLOVA_LLM_URL")
    path = os.getenv("CLOVA_LLM_PATH", "/v3/chat-completions")
    if not api_key or not host:
        missing = []
        if not host:
            missing.append("CLOVA_LLM_URL")
        if not api_key:
            missing.append("CLOVA_LLM_API_KEY")
        msg = f"[live] Missing env: {', '.join(missing)}. Check .env export or install python-dotenv."
        print(msg)
        return None, msg

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8",
        "X-NCP-CLOVASTUDIO-REQUEST-ID": str(uuid.uuid4()),
        "Accept": "application/json",
    }
    data = {
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "너는 채용 전단지를 JSON 하나로 뽑는 봇이다. "
                            "반드시 title, place, work_days, time, hourly_wage, description, raw_text 키만 사용하고 "
                            "추가 텍스트나 키를 넣지 말라."
                        ),
                    }
                ],
            },
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ],
        "topP": 0.8,
        "topK": 0,
        "maxTokens": 400,
        "temperature": 0.7,
        "repetitionPenalty": 1.0,
        "stop": [],
    }
    url = f"{host}{path.rstrip('/')}/{model}"
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as exc:
        err_msg = f"[live] Clova call failed: {exc}"
        try:
            if "resp" in locals():
                err_msg += f" | status={resp.status_code}, body={resp.text[:400]}"
        except Exception:
            pass
        print(err_msg)
        return None, err_msg


def extract_content_json(response: dict) -> dict | None:
    """
    Clova 응답에서 message.content가 JSON 문자열이면 파싱해서 dict로 돌려준다.
    코드펜스나 json 태그가 섞여 있어도 제거를 시도한다.
    """
    if not isinstance(response, dict):
        return None
    content = (
        response.get("result", {})
        .get("message", {})
        .get("content")
    )
    # Clova v3는 content를 [{"type":"text","text":"..."}] 리스트로 줄 수 있으니 문자열로 합친다.
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_val = item.get("text")
                if isinstance(text_val, str):
                    parts.append(text_val)
            elif isinstance(item, str):
                parts.append(item)
        content = "".join(parts)
    if not isinstance(content, str):
        return None
    cleaned = content.strip()
    # ```json ... ``` 코드 펜스를 우선 추출
    fenced = re.search(r"```(?:json)?(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()
    else:
        # 코드펜스가 없으면 문자열에서 첫 번째 JSON 오브젝트를 추출 시도
        candidate = _find_balanced_json(cleaned)
        if candidate:
            cleaned = candidate
    # 마지막으로 다시 한 번 선행/후행 코드펜스 제거 (잔여 ``` 제거)
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print the initial prompt and a sample bad JSON reply (no schema). Use --live to actually call Clova Studio once."
    )
    parser.add_argument(
        "--image",
        type=Path,
        default=DEFAULT_IMAGE,
        help="OCR 입력으로 사용한 샘플 이미지 경로 (기본: ai_modeling/sample/test_post.png)",
    )
    parser.add_argument(
        "--ocr-text",
        help="OCR 결과 텍스트를 직접 지정 (기본: 테스트 전단지에서 추출한 문장 예시)",
    )
    parser.add_argument(
        "--use-ocr",
        action="store_true",
        help="이미지를 Clova OCR로 실제 호출해 텍스트를 추출한 뒤 LLM에 전달한다.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="실제로 Clova Studio chat-completions를 한 번 호출해 실제 응답 JSON을 함께 보여준다.",
    )
    parser.add_argument(
        "--model",
        default="HCX-005",
        help="Clova Studio chat-completions 모델 코드 (기본: HCX-005)",
    )
    args = parser.parse_args()

    started = time.perf_counter()

    # Step 1: OCR (optional)
    ocr_text = args.ocr_text or ""
    ocr_elapsed = None
    if args.use_ocr:
        ocr_started = time.perf_counter()
        ocr_result = call_clova_ocr(args.image)
        ocr_elapsed = time.perf_counter() - ocr_started
        if ocr_result:
            ocr_text = ocr_result

    prompt_display, prompt_llm = build_prompts(ocr_text)
    # 예시 LLM 응답 (OCR 본문 기반이지만 스키마를 어긴 상태)
    example_reply = build_example_llm_reply(ocr_text)

    print("=== OCR sample image ===")
    print(f"path: {args.image.resolve()}")
    print(f"{fmt_size(args.image)}")
    print()
    if args.use_ocr:
        if ocr_elapsed is not None:
            print(f"=== OCR text (Clova) | elapsed: {ocr_elapsed:.2f}s ===")
        else:
            print("=== OCR text (Clova) ===")
        print(ocr_text)
        print()

    live_response = None
    live_error = None
    live_elapsed = None
    if args.live:
        live_started = time.perf_counter()
        live_response, live_error = call_clova_llm(prompt_llm, model=args.model)
        live_elapsed = time.perf_counter() - live_started

    total_elapsed = time.perf_counter() - started
    if total_elapsed >= 1.0:
        elapsed_str = f"{total_elapsed:.3f}s"
    else:
        elapsed_str = f"{total_elapsed*1000:.1f}ms"

    print("=== Run Info ===")
    print(f"Vendor: Clova LLM | model: {args.model} | time: {elapsed_str}")
    print()
    print("=== Prompt sent to LLM ===")
    print(prompt_display)
    print()
    if args.live:
        print("=== Clova LLM 결과 ===")
        if live_response is None:
            print("(live call was skipped or failed; check env and network)")
            if live_error:
                print(live_error)
            rendered = None
        else:
            if live_elapsed is not None:
                print(f"(elapsed: {live_elapsed:.2f}s)")
            rendered = extract_content_json(live_response) or live_response
        print(json.dumps(rendered, ensure_ascii=False, indent=2))

        print()
        print("=== 파싱된 결과 ===")
        parsed = extract_content_json(live_response) if live_response else None
        if parsed is None:
            print("(파싱 실패: message.content가 JSON이 아님 또는 네트워크 문제)")
        else:
            if "raw_text" not in parsed:
                parsed["raw_text"] = ocr_text
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
    else:
        # 라이브 호출을 안 했을 때만 예시를 출력 (스샷 용)
        print("=== Clova LLM 결과 (예시) ===")
        print(json.dumps(example_reply, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
