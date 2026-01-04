#!/usr/bin/env python
"""Create or fetch the default admin user (phone + PIN) and output its UUID."""

from __future__ import annotations

import argparse
import os
import sys
import uuid

from argon2 import PasswordHasher
from sqlmodel import Session, select

from backend_api.app.db.database import engine
from backend_api.app.db.models.auth import User, UserRole


ph = PasswordHasher()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ensure default admin user exists.")
    parser.add_argument("--phone", required=True, help="전화번호 (예: 01000000000)")
    parser.add_argument("--pin", required=True, help="PIN 코드 (4자리)")
    parser.add_argument("--env-output", help="UUID를 기록할 파일 경로")
    return parser.parse_args()


def ensure_admin(phone: str, pin: str) -> uuid.UUID:
    with Session(engine) as session:
        stmt = select(User).where(User.phone_number == phone)
        user = session.exec(stmt).first()
        if user:
            if user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN
            session.commit()
            return user.user_id

        new_user = User(
            phone_number=phone,
            pin_hash=ph.hash(pin),
            role=UserRole.ADMIN,
            is_verified=True,
            nickname="관리자",
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user.user_id


def main() -> None:
    args = parse_args()
    admin_id = ensure_admin(args.phone, args.pin)
    print(f"[ensure_admin] admin_id={admin_id}")
    if args.env_output:
        with open(args.env_output, "w", encoding="utf-8") as fp:
            fp.write(str(admin_id))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ensure_admin] failed: {exc}", file=sys.stderr)
        raise
