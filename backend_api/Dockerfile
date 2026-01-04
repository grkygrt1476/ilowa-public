FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 시스템 의존성 (psycopg2 등 빌드 시 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성 설치 (루트의 requirements.txt 사용)
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# 앱 소스 복사 (백엔드만)
COPY backend_api /app/backend_api

# 기본 실행은 compose에서 uvicorn 커맨드로 지정할 예정
