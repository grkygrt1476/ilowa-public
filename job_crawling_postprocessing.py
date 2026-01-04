#!/usr/bin/env python3
# job_crawling_postprocessing.py 
"""
Post-process the crawled senior forum JSON to fill missing `place`, refine `address`
values using Clova LLM plus Google reverse geocoding, and optionally filter by distance.

Usage:
    python job_crawling_postprocessing.py --input ai_modeling/data/job_seed_seniorforum.json \
        --output ai_modeling/data/job_seed_seniorforum_100.json --filter-junggu
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from ai_modeling.services.clova_llm import CompletionExecutor
except Exception as exc:  # pragma: no cover
    # Only raise error if we actually need the executor (checked later)
    pass

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# 서울특별시 중구청 좌표 기준 (Latitude, Longitude)
JUNG_GU_LAT = 37.563576
JUNG_GU_LNG = 126.997556


def _call_llm_for_place(executor: CompletionExecutor, payload: Dict[str, str]) -> Optional[str]:
    """
    Ask the LLM to suggest a best-fit place name when the source record is empty.
    """
    description = payload.get("description") or ""
    client = payload.get("client") or ""
    address = payload.get("address") or ""
    source = payload.get("source_url") or ""

    prompt = f"""
다음 공고 정보를 참고해 근무지가 들어갈 "place" 문자열을 추천해주세요.

요구사항:
- 한 줄 텍스트만 반환
- 가능한 경우 '○○시니어클럽', '○○복지관' 같은 시설명 사용
- 시설명이 없으면 주소에서 '서울특별시 XX구 YY동' 수준으로 작성
- 추측 불가하면 '서울 미정'으로 작성

정보:
- 설명: {description}
- 기관명(client): {client}
- 주소(address): {address}
- 출처: {source}
"""

    req = {
        "messages": [
            {
                "role": "system",
                "content": "당신은 시니어 일자리 데이터 정제 도우미입니다. 한 줄 텍스트만 출력하세요.",
            },
            {"role": "user", "content": prompt},
        ],
        "maxTokens": 200,
        "temperature": 0.1,
        "topP": 0.9,
        "stream": False,
    }

    try:
        text = executor.execute(req).strip()
    except Exception:
        return None

    if not text:
        return None
    # Strip code block fences if any.
    text = re.sub(r"^```.*?\n", "", text).strip("` \n")
    return text


def _reverse_geocode(lat: Optional[float], lng: Optional[float]) -> Optional[str]:
    """
    Reverse geocode using Google. Requires GOOGLE_GEOCODING_API_KEY or GOOGLE_GEOCODING env.
    """
    if lat is None or lng is None:
        return None
    key = os.getenv("GOOGLE_GEOCODING_API_KEY") or os.getenv("GOOGLE_GEOCODING")
    if not key:
        return None
    try:
        resp = requests.get(
            GOOGLE_GEOCODE_URL,
            params={"latlng": f"{lat},{lng}", "key": key, "language": "ko"},
            timeout=10,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("status") == "OK":
            return data["results"][0]["formatted_address"]
    except Exception:
        return None
    return None


def _clean_address(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.replace("*", "").strip()


def _needs_reverse_lookup(raw_value: str, source_value: Optional[str]) -> bool:
    """
    Decide if we should force reverse geocoding. Conditions:
    - original had masking "*"
    - cleaned value is empty
    - cleaned value lacks digits / detail (<= 3 tokens)
    """
    if source_value and "*" in source_value:
        return True
    value = raw_value.strip()
    if not value:
        return True
    tokens = value.replace(",", " ").split()
    has_digit = any(char.isdigit() for char in value)
    if len(tokens) <= 3 and not has_digit:
        return True
    return False


def _normalize_time_value(token: str) -> Optional[str]:
    """
    Convert arbitrary time text into HH:MM:SS or '미정'.
    """
    if token is None:
        return None
    value = str(token).strip()
    if not value:
        return None

    normalized = value.replace("시", ":").replace("분", ":").replace("초", "")
    normalized = normalized.replace("~", "").replace(" ", "")
    lowered = normalized.lower()
    unknown_tokens = {"미정", "미확정", "미지정", "추후협의", "협의후결정", "추후결정", "미기재", "협의"}
    if lowered in unknown_tokens:
        return "미정"

    digits = re.findall(r"\d+", normalized)
    if not digits:
        return None

    hours = int(digits[0])
    minutes = int(digits[1]) if len(digits) >= 2 else 0
    seconds = int(digits[2]) if len(digits) >= 3 else 0

    hours = max(0, min(hours, 23))
    minutes = max(0, min(minutes, 59))
    seconds = max(0, min(seconds, 59))
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _parse_time_list(value: Optional[object]) -> List[str]:
    """
    Return ordered unique list of normalized times. '미정' overrides everything else.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        tokens = [str(v) for v in value]
    else:
        raw = str(value).replace("~", ",")
        tokens = re.split(r"[,\n/;]+", raw)

    seen = set()
    result: List[str] = []
    for token in tokens:
        normalized = _normalize_time_value(token)
        if not normalized:
            continue
        if normalized == "미정":
            return ["미정"]
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _pad_time_values(values: List[str], target: int) -> List[str]:
    """
    Extend values to target length by repeating the last entry.
    """
    if not values:
        return ["미정"] * target
    if len(values) >= target:
        return values[:target]
    padding = [values[-1]] * (target - len(values))
    return values + padding


def _time_suffixes(count: int) -> List[str]:
    """
    Label splits to make the title human-friendly.
    """
    if count <= 1:
        return [""]
    labels = ["오전", "오후", "저녁", "야간", "심야"]
    suffixes: List[str] = []
    for idx in range(count):
        if idx < len(labels):
            suffixes.append(labels[idx])
        else:
            suffixes.append(f"{idx + 1}차")
    return suffixes


def _append_title_suffix(title: Optional[str], suffix: str) -> str:
    base = (title or "제목 없음").strip()
    suffix = suffix.strip()
    if not suffix:
        return base
    return f"{base} - {suffix}"


def _expand_job_ids(raw_job_id: Optional[object], variant_count: int) -> List[str]:
    """
    Original ID -> base*10 and increments (e.g., 549 -> 5490, 5491, ...).
    Non-numeric IDs fall back to string concatenation.
    """
    raw = str(raw_job_id).strip() if raw_job_id is not None else ""
    if raw.isdigit():
        base = int(raw) * 10
        return [str(base + idx) for idx in range(variant_count)]

    base = f"{raw}0" if raw else "0"
    prefix = base[:-1] if base.endswith("0") else base
    return [f"{prefix}{idx}" for idx in range(variant_count)]


def _split_time_slots(record: Dict[str, object]) -> List[Dict[str, object]]:
    """
    Ensure each record has a single start/end time pair.
    Records with multiple slots are duplicated with suffixes and unique IDs.
    """
    starts = _parse_time_list(record.get("start_time"))
    ends = _parse_time_list(record.get("end_time"))

    if not starts:
        starts = ["미정"]
    if not ends:
        ends = ["미정"]

    slot_count = max(len(starts), len(ends))
    starts = _pad_time_values(starts, slot_count)
    ends = _pad_time_values(ends, slot_count)
    ids = _expand_job_ids(record.get("job_id"), slot_count)
    labels = _time_suffixes(slot_count)

    expanded: List[Dict[str, object]] = []
    for idx in range(slot_count):
        variant = dict(record)
        variant["job_id"] = ids[idx]
        variant["start_time"] = starts[idx]
        variant["end_time"] = ends[idx]
        variant["title"] = _append_title_suffix(record.get("title"), labels[idx])
        expanded.append(variant)
    return expanded


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees).
    """
    R = 6371  # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2) ** 2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def filter_closest_records(records: List[Dict[str, object]], limit: int = 100) -> List[Dict[str, object]]:
    """
    Filter records to keep the closest ones to Jung-gu, Seoul.
    Records without valid coordinates are placed at the end (or ignored).
    """
    valid_records = []
    invalid_records = []

    for record in records:
        try:
            lat = float(record.get("lat", 0))
            lng = float(record.get("lng", 0))
            
            if lat == 0 or lng == 0:
                # Treat 0,0 or missing as invalid/far away
                record["_distance_km"] = float('inf')
                invalid_records.append(record)
                continue

            dist = haversine_distance(JUNG_GU_LAT, JUNG_GU_LNG, lat, lng)
            record["_distance_km"] = dist
            valid_records.append(record)
        except (ValueError, TypeError):
            record["_distance_km"] = float('inf')
            invalid_records.append(record)

    # Sort by calculated distance
    valid_records.sort(key=lambda x: x["_distance_km"])

    # Combine: Closest first, then those with no coords
    combined = valid_records + invalid_records
    
    # Return top K
    # Clean up temporary key before returning if desired, or keep it for debugging.
    # Here we remove it to keep output clean.
    sliced = combined[:limit]
    for r in sliced:
        r.pop("_distance_km", None)
        
    return sliced


def process_records(
    rows: List[Dict[str, object]],
    fill_place: bool = True,
    refine_address: bool = True,
) -> List[Dict[str, object]]:
    
    executor = None
    if fill_place:
        try:
            from ai_modeling.services.clova_llm import CompletionExecutor
            executor = CompletionExecutor()
        except ImportError:
            print("Warning: ai_modeling not found, skipping place filling.")

    updated: List[Dict[str, object]] = []

    for row in rows:
        record = dict(row)
        place_text = (record.get("place") or "").strip()

        if fill_place and not place_text and executor:
            suggestion = _call_llm_for_place(executor, record) or ""
            record["place"] = suggestion.strip()

        if refine_address:
            base_address = _clean_address(record.get("address") if isinstance(record.get("address"), str) else "")
            lat = record.get("lat")
            lng = record.get("lng")
            final_address = base_address
            if _needs_reverse_lookup(base_address, record.get("address") if isinstance(record.get("address"), str) else None):
                geocoded = _reverse_geocode(
                    lat if isinstance(lat, (int, float)) else None,
                    lng if isinstance(lng, (int, float)) else None,
                )
                if geocoded:
                    final_address = geocoded

            record["address"] = final_address or base_address

        updated.extend(_split_time_slots(record))

    return updated


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Post-process crawled jobs JSON for missing place/address.")
    parser.add_argument("--input", required=True, help="Input JSON path")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--no-place", action="store_true", help="Skip filling place via LLM")
    parser.add_argument("--no-address", action="store_true", help="Skip reverse geocoding addresses")
    parser.add_argument("--filter-junggu", action="store_true", help="Filter top 100 jobs closest to Jung-gu, Seoul")
    
    args = parser.parse_args(list(argv) if argv is not None else None)

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    rows = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("Input JSON must be a list of objects.")

    # 1. Process records (Cleaning/Expanding)
    processed = process_records(
        rows,
        fill_place=not args.no_place,
        refine_address=not args.no_address,
    )

    # 2. Optional: Filter closest 100 to Jung-gu
    if args.filter_junggu:
        print(f"Filtering top 100 jobs closest to Jung-gu from {len(processed)} records...")
        processed = filter_closest_records(processed, limit=100)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(processed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(processed)} records to {output_path}")


if __name__ == "__main__":
    main()
