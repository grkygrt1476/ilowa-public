#!/bin/sh
#backend_api/entrypoint.sh
set -eu

# 공통 truthy 체크 함수는 맨 위에 둬서 어디서든 사용할 수 있게 한다.
bool_true() {
    case "${1:-}" in
        true|TRUE|1|yes|YES) return 0 ;;
        *) return 1 ;;
    esac
}

trim() {
    # POSIX-friendly trim (leading/trailing whitespace 제거)
    local var="${1:-}"
    # remove leading whitespace
    var="${var#"${var%%[![:space:]]*}"}"
    # remove trailing whitespace
    var="${var%"${var##*[![:space:]]}"}"
    printf '%s' "$var"
}

# Alembic 실행 시 패키지 경로 보장
export PYTHONPATH="/app"

# 1) DATABASE_URL 구성 (비번 URL 인코딩)
ENC_PW=$(python - <<'PY'
import os
from urllib.parse import quote_plus
print(quote_plus(os.environ["POSTGRES_PASSWORD"]), end="")
PY
)
export DATABASE_URL="postgresql+psycopg2://${POSTGRES_USER}:${ENC_PW}@db:5432/${POSTGRES_DB}"
echo "[ENTRYPOINT] DATABASE_URL -> ${DATABASE_URL}"

# 2) SQLAlchemy 파싱 확인 (선택)
python - <<'PY'
import os
from sqlalchemy.engine import make_url
u = make_url(os.getenv("DATABASE_URL"))
print("[ENTRYPOINT] Parsed USER =", u.username)
print("[ENTRYPOINT] Parsed HOST =", u.host, "DB =", u.database)
PY

# 3) DB 대기 (SQLAlchemy로 핑)
python - <<'PY'
import time, os
from sqlalchemy import create_engine, text
e = create_engine(os.getenv("DATABASE_URL"))
for i in range(12):
    try:
        with e.connect() as c: c.execute(text("select 1"))
        print("[ENTRYPOINT] DB ready"); break
    except Exception as exc:
        print(f"[ENTRYPOINT] wait {i+1}: not ready:", exc); time.sleep(min(2**i, 10))
else:
    raise SystemExit("DB not ready (timeout)")
PY

# 4) Alembic 마이그레이션 (실패 시 중단)
ALEMBIC_CFG="backend_api/alembic.ini"
ALEMBIC_CWD="/app"
ALEMBIC_HEAD_REV="20251203_01"

set +e
python - <<'PY'
import os
import sys
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    has_version = conn.execute(text("SELECT to_regclass('public.alembic_version')")).scalar()
    has_job_post = conn.execute(text("SELECT to_regclass('public.job_post')")).scalar()

if not has_version and has_job_post:
    print("[ENTRYPOINT] alembic_version missing but job_post exists; will stamp.")
    sys.exit(10)

print("[ENTRYPOINT] alembic_version check ok")
PY
status=$?
set -e

if [ $status -eq 10 ]; then
    (cd "${ALEMBIC_CWD}" && alembic -c "${ALEMBIC_CFG}" stamp "${ALEMBIC_HEAD_REV}")
elif [ $status -ne 0 ]; then
    exit $status
fi

(cd "${ALEMBIC_CWD}" && alembic -c "${ALEMBIC_CFG}" upgrade head)

# 4-1) PostGIS/pgvector extension 확인 (없으면 중단)
python - <<'PY'
import os
import sys
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    rows = conn.execute(
        text("SELECT extname FROM pg_extension WHERE extname IN ('postgis','vector')")
    ).fetchall()

exts = {row[0] for row in rows}
missing = [name for name in ("postgis", "vector") if name not in exts]
if missing:
    print(
        "[ENTRYPOINT] Missing extensions: " + ", ".join(missing),
        file=sys.stderr,
    )
    print(
        "[ENTRYPOINT] PostGIS/pgvector extension missing. "
        "DB 이미지를 --build로 다시 올리세요 (docker/postgres.Dockerfile 확인).",
        file=sys.stderr,
    )
    sys.exit(1)

print("[ENTRYPOINT] Extensions OK:", ", ".join(sorted(exts)))
PY

# 5) "user.last_login" 보장 (SQLAlchemy로 실행)
python - <<'PY' || echo "[WARN] DDL step skipped/failed (will not block startup)"
import os
from sqlalchemy import create_engine, text
e = create_engine(os.getenv("DATABASE_URL"))
ddl = """
DO $$
BEGIN
   IF to_regclass('public.user') IS NOT NULL THEN
      ALTER TABLE "user" ADD COLUMN IF NOT EXISTS last_login timestamp without time zone;
      ALTER TABLE "user" ALTER COLUMN last_login DROP NOT NULL;
      ALTER TABLE "user" ALTER COLUMN last_login SET DEFAULT NOW();
   END IF;
END $$;
"""
with e.begin() as conn:
    conn.execute(text(ddl))
print("[ENTRYPOINT] last_login DDL ensured")
PY

# 5-1) SQLModel 기반 테이블 보장 (특히 user 테이블 선행 생성)
python - <<'PY' || echo "[WARN] SQLModel table ensure failed"
from backend_api.app.db.database import create_db_and_tables
create_db_and_tables()
print("[ENTRYPOINT] Base tables ensured via SQLModel")
PY

# 5-2) work_days 컬럼을 JSON으로 강제 (과거 VARCHAR(10) 호환)
python - <<'PY' || echo "[WARN] work_days JSON migration failed (continuing)"
import json
import os
from sqlalchemy import create_engine, text

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise SystemExit("DATABASE_URL not set")

engine = create_engine(db_url)

with engine.begin() as conn:
    result = conn.execute(
        text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'job_post'
              AND column_name = 'work_days'
            """
        )
    ).scalar()
    if not result:
        print("[ENTRYPOINT] job_post.work_days column missing; skipping JSON migration")
    elif result.lower() in ("json", "jsonb"):
        print("[ENTRYPOINT] job_post.work_days already JSON")
    else:
        print("[ENTRYPOINT] Migrating job_post.work_days from", result, "to JSON")
        conn.execute(text("ALTER TABLE job_post DROP COLUMN IF EXISTS work_days_tmp"))
        conn.execute(
            text("ALTER TABLE job_post ADD COLUMN work_days_tmp JSON DEFAULT '[]'::json NOT NULL")
        )
        rows = conn.execute(text("SELECT id, work_days FROM job_post")).fetchall()
        for job_id, raw_days in rows:
            parsed = []
            if raw_days is None:
                parsed = []
            elif isinstance(raw_days, list):
                parsed = [str(v) for v in raw_days if v]
            elif isinstance(raw_days, str):
                trimmed = raw_days.strip()
                if trimmed:
                    try:
                        candidate = json.loads(trimmed)
                        if isinstance(candidate, list):
                            parsed = [str(v) for v in candidate if v]
                        else:
                            parsed = []
                    except json.JSONDecodeError:
                        parsed = [seg.strip() for seg in trimmed.split(",") if seg.strip()]
            else:
                parsed = []
            conn.execute(
                text("UPDATE job_post SET work_days_tmp = CAST(:val AS JSON) WHERE id = :id"),
                {"val": json.dumps(parsed), "id": str(job_id)},
            )
        conn.execute(text("ALTER TABLE job_post DROP COLUMN work_days"))
        conn.execute(text("ALTER TABLE job_post RENAME COLUMN work_days_tmp TO work_days"))
        conn.execute(text("ALTER TABLE job_post ALTER COLUMN work_days SET DEFAULT '[]'::json"))
        conn.execute(text("ALTER TABLE job_post ALTER COLUMN work_days SET NOT NULL"))
        print("[ENTRYPOINT] job_post.work_days column migrated to JSON")
PY

# 6) 관리자 계정 자동 생성 (전화번호 01000000000 / PIN 0000)
if bool_true "${AUTO_ADMIN_ENABLED:-true}"; then
    ADMIN_PHONE="${ADMIN_PHONE:-01000000000}"
    ADMIN_PIN="${ADMIN_PIN:-0000}"
    echo "[ENTRYPOINT] Ensuring admin user ($ADMIN_PHONE) exists"
    python -m backend_api.scripts.ensure_admin \
        --phone "${ADMIN_PHONE}" \
        --pin "${ADMIN_PIN}" \
        --env-output /tmp/admin_uuid.txt || echo "[WARN] Admin ensure failed"
    if [ -f /tmp/admin_uuid.txt ]; then
        ADMIN_USER_ID="$(cat /tmp/admin_uuid.txt)"
        export ADMIN_USER_ID
        echo "[ENTRYPOINT] Admin UUID = ${ADMIN_USER_ID}"
    fi
fi

# 7) 초기 소일거리 데이터 시드 (선택)
SEED_OWNER_RAW="${SEED_JOBS_OWNER_ID:-${ADMIN_USER_ID:-}}"
SEED_OWNER="$(trim "${SEED_OWNER_RAW}")"

if [ -n "${SEED_OWNER}" ]; then
    DEFAULT_SEED_PATH="ai_modeling/data_samples/demo_jobs_50.json"
    CSV_PATH="${SEED_JOBS_JSON:-${SEED_JOBS_CSV:-${DEFAULT_SEED_PATH}}}"

    echo "[ENTRYPOINT] Seeding owner=${SEED_OWNER}, CSV_PATH=${CSV_PATH}"

    if [ ! -f "${CSV_PATH}" ]; then
        echo "[ENTRYPOINT] ⚠️  SEED owner configured but CSV not found at ${CSV_PATH}"
    else
        CLEAR_FLAG=""
        if bool_true "${SEED_JOBS_CLEAR:-true}"; then
            CLEAR_FLAG="--clear"
        fi

        LIMIT_ARGS=""
        if [ -n "${SEED_JOBS_LIMIT:-}" ]; then
            LIMIT_ARGS="--limit ${SEED_JOBS_LIMIT}"
        fi

        GEOCODE_ARGS=""
        if bool_true "${SEED_JOBS_GEOCODE:-true}"; then
            GOOGLE_KEY="${GOOGLE_GEOCODING_API_KEY:-${GOOGLE_GEOCODING:-}}"
            if [ -n "${NAVER_MAPS_CLIENT_ID:-}" ] && [ -n "${NAVER_MAPS_CLIENT_SECRET:-}" ]; then
                GEOCODE_ARGS="--geocode --cache .naver_geocode_cache.json"
            fi
            if [ -n "${GOOGLE_KEY:-}" ]; then
                GEOCODE_ARGS="${GEOCODE_ARGS} --google-geocode"
            fi
            if [ -z "${GEOCODE_ARGS}" ]; then
                echo "[ENTRYPOINT] ⚠️  Geocode requested but no NAVER or GOOGLE keys available; skipping."
            fi
        fi

        echo "[ENTRYPOINT] Seeding AI jobs from ${CSV_PATH} (owner=${SEED_OWNER})"
        python -m backend_api.scripts.import_ai_jobs \
            --owner "${SEED_OWNER}" \
            --csv "${CSV_PATH}" \
            ${CLEAR_FLAG} \
            ${LIMIT_ARGS} \
            ${GEOCODE_ARGS} || echo "[WARN] Job seeding failed (continuing)"

        DEFAULT_EMBEDDING_PATH="ai_modeling/data_samples/demo_jobs_50_with_embeddings.csv"
        EMBEDDING_PATH="${SEED_JOBS_EMBEDDINGS_CSV:-${DEFAULT_EMBEDDING_PATH}}"
        if [ -f "${EMBEDDING_PATH}" ]; then
            echo "[ENTRYPOINT] Updating embeddings from ${EMBEDDING_PATH}"
            python -m backend_api.scripts.import_ai_job_embeddings \
                --csv "${EMBEDDING_PATH}" || echo "[WARN] Embedding update failed (continuing)"
        else
            echo "[ENTRYPOINT] ⚠️  Embedding CSV not found at ${EMBEDDING_PATH}"
        fi
    fi
fi

# 8) 앱 시작
exec uvicorn backend_api.app.main:app --host 0.0.0.0 --port 8000 --reload
