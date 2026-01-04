#!/usr/bin/env python
"""CSV → JSON 변환 스크립트 (Google Geocoding 사용)"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from backend_api.app.services.google_geocoder import GoogleGeocoder


KEEP_FIELDS = [
    "job_id",
    "title",
    "description",
    "place",
    "address",
    "work_days",
    "start_time",
    "end_time",
    "participants",
    "client",
    "hourly_wage",
    "wage",
    "wage_amount",
    "pay_text",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CSV를 Google Geocoding으로 lat/lng 포함 JSON으로 변환")
    parser.add_argument("--csv", required=True, type=Path, help="입력 CSV 경로")
    parser.add_argument("--output", required=True, type=Path, help="출력 JSON 경로")
    parser.add_argument("--limit", type=int, default=None, help="최대 처리 행 수")
    return parser.parse_args()


def load_rows(path: Path, limit: Optional[int]) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        rows: List[Dict[str, str]] = []
        for idx, row in enumerate(reader):
            rows.append(row)
            if limit is not None and idx + 1 >= limit:
                break
    return rows


def main() -> None:
    load_dotenv()
    args = parse_args()
    geocoder = GoogleGeocoder()

    rows = load_rows(args.csv, args.limit)
    if not rows:
        print("⚠️ CSV에 데이터가 없습니다.")
        return

    output_rows: List[Dict[str, object]] = []
    for row in rows:
        query = (row.get("address") or row.get("place") or row.get("title") or "").strip()
        lat = lng = None
        if query:
            coords = geocoder.geocode(query)
            if coords:
                lat, lng = coords
        if lat is None or lng is None:
            print(f"[WARN] 좌표를 찾지 못했습니다: {query}")
            continue

        record: Dict[str, object] = {field: row.get(field) for field in KEEP_FIELDS if field in row}
        record["lat"] = lat
        record["lng"] = lng
        output_rows.append(record)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fp:
        json.dump(output_rows, fp, ensure_ascii=False, indent=2)
    print(f"✅ 변환 완료: {len(output_rows)} rows -> {args.output}")


if __name__ == "__main__":
    main()
