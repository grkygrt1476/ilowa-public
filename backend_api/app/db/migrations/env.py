from __future__ import annotations
import os

from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# ---- Alembic 기본 설정 로드 ----
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---- 메타데이터(autogenerate용) 로드 ----
from backend_api.app.db import models  # noqa: F401
target_metadata = SQLModel.metadata

# ---- DB URL 구성 (ENV 우선, 없으면 POSTGRES_*로 DSN 생성) ----
def make_dsn() -> str | None:
    user = os.getenv("POSTGRES_USER")
    pwd  = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("DB_HOST", "db")   # 컨테이너 간 통신 기본 host
    port = os.getenv("DB_PORT", "5432")
    db   = os.getenv("POSTGRES_DB")
    if not all([user, pwd, host, db]):
        return None
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"

url = os.getenv("DATABASE_URL") or make_dsn()
if url:
    # Alembic(configparser) 의 % 인터폴레이션 이슈 방지
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

# ---- 마이그레이션 실행 함수 ----
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
