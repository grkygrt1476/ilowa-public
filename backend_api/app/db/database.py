from typing import Generator
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text


# settings에서 .env를 읽어오는 게 일관적입니다.
# (os.environ 직접 읽어도 되지만, 프로젝트가 이미 pydantic-settings를 쓰고 있으니 settings 권장)
from backend_api.app.core.config import settings

# 1) DB URL
DATABASE_URL = settings.DATABASE_URL  # 예: "postgresql+psycopg://user:pass@localhost:5432/ilowa_db"

# 2) 엔진 생성
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_recycle=3600,
)

# 3) 테이블 생성 헬퍼 (개발 초기용)
def _ensure_user_table_columns() -> None:
    """SQLite 개발 DB를 사용 중일 때 누락된 user 컬럼을 보강한다."""

    if engine.url.get_backend_name() != "sqlite":
        return

    expected_columns = {
        "preferences": "JSON DEFAULT '{}'",
        "point_balance": "INTEGER NOT NULL DEFAULT 0",
        "is_onboarding_complete": "BOOLEAN NOT NULL DEFAULT 0",
    }

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info('user')")).fetchall()
        existing = {row[1] for row in rows}

        for column, ddl in expected_columns.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE user ADD COLUMN {column} {ddl}"))


def create_db_and_tables() -> None:
    # ✅ 프로젝트 네임스페이스에 맞게 경로 수정
    from backend_api.app.db.models import (  # noqa: F401
        JobApplication,
        JobPost,
        MediaUpload,
        OTPVerificationRequest,
        User,
        Notification,
    )

    SQLModel.metadata.create_all(engine)
    _ensure_user_table_columns()

# 4) FastAPI 의존성 (라우터에서 쓰는 이름과 일치!)
def get_db() -> Generator[Session, None, None]:
    """요청마다 새로운 DB 세션을 생성하고, 요청 완료 후 닫습니다."""
    with Session(engine) as session:
        yield session
