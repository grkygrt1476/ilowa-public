from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session, select

from backend_api.app.db.models.jobs import JobPost, JobStatus

logger = logging.getLogger(__name__)

DAY_CODES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
DEFAULT_COORD = (37.5665, 126.9780)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_work_days(bits: str) -> List[str]:
    digits = (bits or "").strip().ljust(7, "0")
    return [code for digit, code in zip(digits[:7], DAY_CODES) if digit == "1"]


def _load_csv_rows(csv_path: Path, limit: Optional[int]) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        rows: List[Dict[str, str]] = []
        for idx, row in enumerate(reader):
            rows.append(row)
            if limit is not None and idx + 1 >= limit:
                break
    return rows


def _load_json_rows(json_path: Path, limit: Optional[int]) -> List[Dict[str, str]]:
    with json_path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise ValueError(f"JSON 데이터는 list 형식이어야 합니다: {json_path}")
    rows: List[Dict[str, str]] = []
    for idx, item in enumerate(data):
        if isinstance(item, dict):
            rows.append({k: v for k, v in item.items()})
        else:
            raise ValueError(f"JSON 항목이 dict가 아닙니다 (index={idx})")
        if limit is not None and idx + 1 >= limit:
            break
    return rows


def _load_rows(source_path: Path, limit: Optional[int]) -> List[Dict[str, str]]:
    suffix = source_path.suffix.lower()
    if suffix == ".json":
        return _load_json_rows(source_path, limit)
    return _load_csv_rows(source_path, limit)


def _guess_coordinates(text: Optional[str]) -> Tuple[float, float]:
    """Rough fallback to keep markers visible even without geocoding."""
    if not text:
        return DEFAULT_COORD

    mapping = {
        "성동": (37.5636, 127.0364),
        "강남": (37.5172, 127.0473),
        "서초": (37.4836, 127.0327),
        "마포": (37.5568, 126.9101),
        "송파": (37.5145, 127.1056),
        "은평": (37.6176, 126.9227),
        "부산": (35.1796, 129.0756),
        "대구": (35.8714, 128.6014),
        "광주": (35.1595, 126.8526),
        "대전": (36.3504, 127.3845),
    }

    for key, coords in mapping.items():
        if key in text:
            return coords
    return DEFAULT_COORD


def _coerce_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value in (None, "", "null"):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.]", "", value)
        if not cleaned:
            return default
        try:
            return int(float(cleaned))
        except ValueError:
            return default
    return default


def _coerce_float(value: Any) -> Optional[float]:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_csv_job_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        raw = value.get("csv_job_id")
    else:
        raw = value
    if raw is None:
        return None
    normalized = str(raw).strip()
    return normalized or None


def seed_jobs_from_csv(
    session: Session,
    *,
    owner_id: UUID,
    csv_path: Path,
    limit: Optional[int] = None,
    clear_existing: bool = False,
    geocoders: Sequence[Any] = (),
) -> int:
    """Insert jobs from CSV into job_post table.

    Args:
        session: Active SQLModel session.
        owner_id: Owner for inserted jobs.
        csv_path: CSV file path.
        limit: Optional limit on rows.
        clear_existing: Delete existing ai_seed jobs before insert.
        geocoders: Sequence of geocoder objects exposing geocode(query) -> (lat, lng).

    Returns:
        Number of inserted jobs.
    """
    rows = _load_rows(csv_path, limit)
    if not rows:
        return 0

    if clear_existing:
        to_delete = session.exec(
            select(JobPost).where(JobPost.source == "ai_seed")
        ).all()
        for job in to_delete:
            session.delete(job)
        if to_delete:
            logger.info("Removed %s existing ai_seed jobs", len(to_delete))

    existing_pairs: set[tuple[str, str]] = set()
    existing_csv_ids: set[str] = set()
    existing_stmt = select(
        JobPost.title,
        JobPost.address,
        JobPost.source,
        JobPost.ai_summary,
    )
    for title, address, source, summary in session.exec(existing_stmt):
        key = (_normalize_text(title), _normalize_text(address))
        existing_pairs.add(key)
        if source == "ai_seed":
            csv_id = _extract_csv_job_id(summary)
            if csv_id:
                existing_csv_ids.add(csv_id)

    geocoders = list(geocoders or [])

    inserted = 0
    for row in rows:
        key = (_normalize_text(row.get("title")), _normalize_text(row.get("address")))
        csv_job_id = _extract_csv_job_id(row.get("job_id"))
        if csv_job_id:
            if csv_job_id in existing_csv_ids:
                continue
        else:
            if key in existing_pairs:
                continue

        lat = _coerce_float(row.get("lat"))
        lng = _coerce_float(row.get("lng"))
        query_parts = [row.get("address"), row.get("place")]
        query = " ".join([p for p in query_parts if p]).strip()
        if (lat is None or lng is None) and query and geocoders:
            for geocoder in geocoders:
                try:
                    coords = geocoder.geocode(query)
                except Exception as exc:  # pragma: no cover - network issues
                    logger.warning("Geocoder %s failed for '%s': %s", geocoder.__class__.__name__, query, exc)
                    coords = None
                if coords:
                    if lat is None:
                        lat = coords[0]
                    if lng is None:
                        lng = coords[1]
                    break
        if lat is None or lng is None:
            lat_guess, lng_guess = _guess_coordinates(row.get("address") or row.get("place"))
            if lat is None:
                lat = lat_guess
            if lng is None:
                lng = lng_guess

        job = JobPost(
            owner_id=owner_id,
            title=row.get("title") or "제목 미상",
            description=row.get("description") or "상세 설명 미등록",
            requirements=None,
            category=None,
            place=row.get("place"),
            address=row.get("address"),
            location=row.get("address"),
            work_days=_parse_work_days(row.get("work_days") or ""),
            start_time=row.get("start_time"),
            end_time=row.get("end_time"),
            participants=_coerce_int(row.get("participants"), default=1),
            client=row.get("client"),
            hourly_wage=_coerce_int(row.get("hourly_wage")),
            pay_text=row.get("wage_amount") or row.get("pay_text"),
            wage=row.get("wage_amount") or row.get("pay_text"),
            lat=lat,
            lng=lng,
            status=JobStatus.OPEN,
            source="ai_seed",
            ai_confidence=0.95,
            ai_summary={"csv_job_id": row.get("job_id")},
        )
        session.add(job)
        if csv_job_id:
            existing_csv_ids.add(csv_job_id)
        existing_pairs.add(key)
        inserted += 1

    session.commit()

    try:
        session.exec(
            text(
                "UPDATE job_post "
                "SET geom = ST_SetSRID(ST_MakePoint(lng, lat), 4326) "
                "WHERE geom IS NULL AND lat IS NOT NULL AND lng IS NOT NULL"
            )
        )
        session.commit()
    except Exception as exc:  # pragma: no cover - optional if PostGIS not present
        session.rollback()
        logger.warning("PostGIS geom backfill skipped: %s", exc)
    return inserted
