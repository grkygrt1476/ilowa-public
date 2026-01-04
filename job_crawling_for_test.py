#!/usr/bin/env python3
"""
Utility script to crawl seniorforum.net postings and convert them into AI seeding JSON.
Support Batch Crawling and Merging.

Usage (Crawl):
    python job_crawling_for_test.py --mode crawl --from-id 634 --to-id 600
    # Output: ai_modeling/data/job_seed_seniorforum_634-600.json

Usage (Merge):
    python job_crawling_for_test.py --mode merge \
        --inputs ai_modeling/data/job_seed_seniorforum_634-600.json ai_modeling/data/job_seed_seniorforum_600-550.json \
        --output ai_modeling/data/job_seed_seniorforum_merged.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from glob import glob
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

# ai_modeling 모듈을 사용할 수 있도록 현재 프로젝트 루트를 PYTHONPATH에 추가
try:
    REPO_ROOT = Path(__file__).resolve().parent
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        def load_dotenv(path: Optional[str] = None) -> None:
            target = Path(path or ".env")
            if not target.exists():
                return
            for raw_line in target.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                cleaned = value.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), cleaned)

    from ai_modeling.services.clova_llm import CompletionExecutor
except ImportError as exc:  # pragma: no cover - guard for CLI usage
    raise SystemExit(
        f"Error: ai_modeling 또는 의존 모듈을 불러오지 못했습니다 ({exc}). "
        "프로젝트 루트에서 실행하고, 필요한 패키지가 설치되어 있는지 확인하세요."
    ) from exc

ARTICLE_URL_FORMAT = "https://seniorforum.net/seoul/{}"
DEFAULT_DIR = str(REPO_ROOT / "ai_modeling" / "data")
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
WORK_DAY_CODES = ["월", "화", "수", "목", "금", "토", "일"]


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_article(html: str) -> Optional[Tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article#bo_v")
    if not article:
        return None
    
    title_el = article.select_one(".bo_v_tit") or article.find("h1")
    title = _clean_text(title_el.get_text()) if title_el else "제목 없음"

    for tag in article(["script", "style", "button", "noscript", "iframe"]):
        tag.extract()
    
    body_text = _clean_text(article.get_text(separator="\n"))
    return title, body_text


def _call_clova_llm(executor: CompletionExecutor, text: str) -> Dict[str, str]:
    prompt = f"""
아래는 시니어 구인 웹 페이지의 본문 내용입니다. 내용을 분석하여 지정된 JSON 포맷으로 추출하세요.

[필수 추출 항목 및 규칙]
1. title: 공고 제목
2. description: 업무 내용 요약 (근무시간/주당 총 시간/급여 산정 방식 등 숫자 표현이 있으면 문장으로 포함하세요.)
3. place: 근무지 명칭. 우선 사업장/시설명(예: ○○시니어클럽, ○○복지관 등)을 사용하고, 그런 정보가 없다면 client 이름에서 장소성을 가진 단어를 사용하세요. 그래도 없으면 address를 시/구/동 수준으로 축약하여 사용하세요.
4. address: 상세 주소 (대한민국 주소 형식으로 작성하고 `*` 같은 마스킹 문자는 쓰지 마세요. 문맥에서 유추 가능한 가장 구체적인 주소를 적습니다.)
5. work_days: "1111111" 포맷 (월~일). 요일 정보 없으면 "미정".
6. start_time, end_time: "HH:MM:SS" 포맷. 범위가 "08:00~20:00"처럼 주어지면 start_time="08:00:00", end_time="20:00:00". 정보가 없거나 파싱 불가하면 "미정".
7. participants: 모집 인원(숫자 문자열).
8. client: 채용 주체.
9. hourly_wage: 시급(숫자 문자열). 시급 변환이 가능한 단서(예: 주 8시간*4주 352,000원)가 있다면 시급으로 계산해 숫자만 입력, 계산 불가하면 빈 문자열.
10. contact_phone: 담당자 연락처 (로그인 ID, 단순 숫자 제외, 010/02 등 전화번호 형식만).

[입력 텍스트]
{text}

[출력 형식]
오직 JSON 문자열만 출력하세요. description에는 위 숫자 정보가 있으면 그대로 서술하세요.
"""
    req = {
        "messages": [
            {"role": "system", "content": "당신은 구인 공고 정보를 JSON으로 변환하는 AI입니다."},
            {"role": "user", "content": prompt},
        ],
        "maxTokens": 1000,
        "temperature": 0.1,
        "topP": 0.9,
        "stream": False,
    }
    response = executor.execute(req)
    try:
        cleaned_res = re.sub(r"```json|```", "", response).strip()
        return json.loads(cleaned_res)
    except Exception as exc:
        raise RuntimeError(f"LLM 응답 파싱 실패: {response}") from exc


def _geocode(addresses: List[str]) -> Tuple[Optional[float], Optional[float]]:
    key = os.getenv("GOOGLE_GEOCODING_API_KEY") or os.getenv("GOOGLE_GEOCODING")
    if not key:
        return None, None
    for addr in addresses:
        if not addr:
            continue
        clean_addr = re.sub(r"\(.*?\)", "", addr).strip()
        if not clean_addr:
            continue
        try:
            resp = requests.get(
                GOOGLE_GEOCODE_URL,
                params={"address": clean_addr, "key": key, "language": "ko"},
                timeout=10,
            )
            data = resp.json()
            if resp.status_code == 200 and data.get("status") == "OK":
                loc = data["results"][0]["geometry"]["location"]
                return loc.get("lat"), loc.get("lng")
        except Exception:
            continue
    return None, None


def _work_days_to_digits(value: str) -> str:
    if not value or value == "미정": return "미정"
    if re.match(r"^[01]{7}$", value): return value
    
    normalized = value.replace("요일", "")
    digits = ["0"] * 7
    for idx, day in enumerate(WORK_DAY_CODES):
        if day in normalized: digits[idx] = "1"
    if any(w in normalized for w in ["평일", "주중", "월~금"]):
        for idx in range(5): digits[idx] = "1"
    if any(w in normalized for w in ["주말", "토일"]):
        digits[5] = digits[6] = "1"
    res = "".join(digits)
    return res if "1" in res else "미정"


def crawl_articles(from_id: int, to_id: int, delay: float) -> List[Dict]:
    executor = CompletionExecutor()
    results = []
    seen_titles = set()
    
    step = -1 if from_id > to_id else 1
    print(f"[*] Crawling range: {from_id} -> {to_id}")

    for article_id in range(from_id, to_id + step, step):
        url = ARTICLE_URL_FORMAT.format(article_id)
        try:
            print(f"Processing {article_id}...", end=" ", flush=True)
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                print("Skip(Status)")
                continue
            
            parsed = _extract_article(resp.text)
            if not parsed:
                print("Skip(Content)")
                continue
            
            title, body = parsed
            if title in seen_titles:
                print("Skip(DupTitle)")
                continue
            seen_titles.add(title)

            llm_data = _call_clova_llm(executor, body)
            lat, lng = _geocode([
                llm_data.get("address") or "",
                llm_data.get("place") or "",
                llm_data.get("client") or "",
            ])
            
            record = {
                "job_id": str(article_id),
                "title": llm_data.get("title") or title,
                "description": llm_data.get("description") or body[:200],
                "place": llm_data.get("place") or "",
                "address": llm_data.get("address") or "",
                "work_days": _work_days_to_digits(llm_data.get("work_days")),
                "start_time": llm_data.get("start_time") or "미정",
                "end_time": llm_data.get("end_time") or "미정",
                "participants": llm_data.get("participants") or "",
                "client": llm_data.get("client") or "",
                "hourly_wage": llm_data.get("hourly_wage") or "",
                "contact_phone": llm_data.get("contact_phone") or "",
                "lat": lat,
                "lng": lng,
                "source_url": url
            }
            results.append(record)
            print("Saved")
            time.sleep(delay)
        except Exception as e:
            print(f"Error: {e}")
    
    return results


def merge_json_files(input_files: List[str], output_file: str):
    """여러 JSON 파일을 읽어 job_id 기준으로 중복을 제거하고 합칩니다."""
    merged_data = {}  # job_id: record
    file_count = 0
    
    print(f"[*] Merging {len(input_files)} files...")
    
    for filepath in input_files:
        # 와일드카드 지원 (예: *.json)
        for f in glob(filepath):
            try:
                with open(f, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    file_count += 1
                    for item in data:
                        jid = item.get('job_id')
                        # job_id가 있으면 그걸로 중복 제거, 없으면 title로
                        key = jid if jid else item.get('title')
                        
                        if key not in merged_data:
                            merged_data[key] = item
                        else:
                            # (선택사항) 필요하다면 정보 업데이트 로직을 여기에 추가
                            pass
            except Exception as e:
                print(f"[WARN] Failed to load {f}: {e}")

    result_list = list(merged_data.values())
    
    # 결과 저장
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_list, f, ensure_ascii=False, indent=2)
        
    print(f"[Success] Merged {file_count} files into '{output_file}'")
    print(f"          Total unique records: {len(result_list)}")


def main():
    parser = argparse.ArgumentParser(description="Job Crawler & Merger")
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Mode: crawl or merge")

    # === Crawl Mode ===
    parser_crawl = subparsers.add_parser("crawl", help="Crawl seniorforum data")
    parser_crawl.add_argument("--from-id", type=int, required=True, help="Start ID (Latest)")
    parser_crawl.add_argument("--to-id", type=int, required=True, help="End ID (Oldest)")
    parser_crawl.add_argument("--output", type=str, help="Output file path (Optional)")
    parser_crawl.add_argument("--delay", type=float, default=1.0)

    # === Merge Mode ===
    parser_merge = subparsers.add_parser("merge", help="Merge multiple JSON files")
    parser_merge.add_argument("--inputs", nargs="+", required=True, help="Input JSON files (wildcards allowed)")
    parser_merge.add_argument("--output", type=str, required=True, help="Merged Output file path")

    args = parser.parse_args()

    if args.mode == "crawl":
        # 출력 파일명 자동 생성 로직
        if not args.output:
            filename = f"job_seed_seniorforum_{args.from_id}-{args.to_id}.json"
            args.output = os.path.join(DEFAULT_DIR, filename)
        
        jobs = crawl_articles(args.from_id, args.to_id, args.delay)
        if jobs:
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(jobs, f, ensure_ascii=False, indent=2)
            print(f"[Done] Saved {len(jobs)} jobs to {args.output}")
        else:
            print("[Done] No jobs found in this range.")

    elif args.mode == "merge":
        merge_json_files(args.inputs, args.output)


if __name__ == "__main__":
    main()
