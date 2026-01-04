#!/usr/bin/env python
"""Import seed jobs from CSV into job_post table with optional geocoding."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session, select

from backend_api.app.db.database import engine, create_db_and_tables
from backend_api.app.db.models import User, UserRole
from backend_api.app.services.google_geocoder import GoogleGeocoder
from backend_api.app.services.job_seeder import seed_jobs_from_csv
from backend_api.app.services.naver_geocoder import NaverGeocoder
from backend_api.scripts.ensure_admin import ensure_admin


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = Path(
    os.getenv(
        "SEED_JOBS_JSON",
        os.getenv("SEED_JOBS_CSV", str(REPO_ROOT / "ai_modeling" / "data_samples" / "demo_jobs_50.json")),
    )
)
DEFAULT_ADMIN_PHONE = "01000000000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import AI CSV into job_post table")
    parser.add_argument(
        "--owner",
        help="Owner user UUID. 생략하면 관리자 계정을 자동 탐색합니다.",
    )
    parser.add_argument(
        "--owner-phone",
        help="Owner 계정을 찾을 전화번호 (기본: ADMIN_PHONE 또는 01000000000).",
    )
    parser.add_argument(
        "--admin-pin",
        help="관리자 계정 자동 생성 시 사용할 PIN (기본: ADMIN_PIN 또는 0000).",
    )
    parser.add_argument(
        "--no-admin-autocreate",
        action="store_true",
        help="관리자 계정을 자동 생성하지 않습니다.",
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Seed path (.csv/.json)")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to import")
    parser.add_argument("--clear", action="store_true", help="Delete existing ai_seed jobs")
    parser.add_argument(
        "--ensure-schema",
        action="store_true",
        help="SQLModel create_all로 스키마를 보장합니다 (권장: alembic 선행).",
    )
    parser.add_argument("--geocode", action="store_true", help="Enable Naver geocoding")
    parser.add_argument(
        "--google-geocode",
        action="store_true",
        help="Enable Google geocoding (requires GOOGLE_GEOCODING_API_KEY/GOOGLE_GEOCODING)",
    )
    parser.add_argument("--cache", type=Path, default=Path(".naver_geocode_cache.json"))
    return parser.parse_args()


def _maybe_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError as exc:  # pragma: no cover - CLI validation
        raise SystemExit(f"[import_ai_jobs] 잘못된 UUID 값입니다: '{value}'") from exc


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits or None


def _resolve_owner_uuid(
    session: Session,
    *,
    explicit_owner: Optional[str],
    owner_phone: Optional[str],
    admin_pin: Optional[str],
    allow_autocreate: bool,
) -> uuid.UUID:
    for candidate in (
        explicit_owner,
        os.getenv("SEED_JOBS_OWNER_ID"),
        os.getenv("ADMIN_USER_ID"),
    ):
        parsed = _maybe_uuid(candidate)
        if parsed:
            return parsed

    phone_candidates: list[str] = []
    for source in (owner_phone, os.getenv("ADMIN_PHONE"), DEFAULT_ADMIN_PHONE):
        normalized = _normalize_phone(source)
        if normalized and normalized not in phone_candidates:
            phone_candidates.append(normalized)

    admin_pin = (admin_pin or os.getenv("ADMIN_PIN") or "0000").strip()
    attempted_autocreate = False

    for phone in phone_candidates:
        stmt = select(User).where(User.phone_number == phone)
        user = session.exec(stmt).first()
        if user:
            return user.user_id
        if allow_autocreate and not attempted_autocreate and admin_pin:
            attempted_autocreate = True
            try:
                created = ensure_admin(phone, admin_pin)
                return created
            except Exception as exc:  # pragma: no cover - DB/validation errors
                print(f"[import_ai_jobs] 관리자 자동 생성 실패: {exc}", file=sys.stderr)

    admin = session.exec(
        select(User)
        .where(User.role == UserRole.ADMIN)
        .order_by(User.created_at.asc())
    ).first()
    if admin:
        return admin.user_id

    raise SystemExit(
        "[import_ai_jobs] owner를 찾지 못했습니다. "
        "--owner UUID를 직접 지정하거나 ADMIN_* 환경변수를 확인하세요."
    )


def _ensure_schema_ready(session: Session) -> None:
    has_version = session.exec(
        text("SELECT to_regclass('public.alembic_version')")
    ).scalar()
    has_job_post = session.exec(
        text("SELECT to_regclass('public.job_post')")
    ).scalar()
    if not has_job_post:
        raise SystemExit(
            "[import_ai_jobs] job_post 테이블이 없습니다. "
            "먼저 alembic -c backend_api/alembic.ini upgrade head 를 실행하세요."
        )
    if not has_version:
        raise SystemExit(
            "[import_ai_jobs] alembic_version 테이블이 없습니다. "
            "먼저 alembic -c backend_api/alembic.ini upgrade head 를 실행하세요 "
            "(또는 --ensure-schema 사용)."
        )


def main() -> None:
    args = parse_args()
    if args.ensure_schema:
        create_db_and_tables()

    geocoders = []
    if args.geocode:
        geocoders.append(NaverGeocoder(cache_path=args.cache))
    if args.google_geocode:
        geocoders.append(GoogleGeocoder())

    with Session(engine) as session:
        if not args.ensure_schema:
            _ensure_schema_ready(session)
        owner_id = _resolve_owner_uuid(
            session,
            explicit_owner=args.owner,
            owner_phone=args.owner_phone,
            admin_pin=args.admin_pin,
            allow_autocreate=not args.no_admin_autocreate,
        )
        print(f"[import_ai_jobs] owner={owner_id}")
        inserted = seed_jobs_from_csv(
            session,
            owner_id=owner_id,
            csv_path=args.csv,
            limit=args.limit,
            clear_existing=args.clear,
            geocoders=geocoders,
        )
        print(f"Inserted {inserted} jobs")


if __name__ == "__main__":
    main()
