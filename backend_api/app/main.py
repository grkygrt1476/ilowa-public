import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from backend_api.app.core.config import settings
from backend_api.app.db import database
from backend_api.app.api.v1 import (
    admin,
    applications,
    auth,
    jobs,
    matches,
    users,
    profile,
    notifications,
)
from backend_api.app.routes import ai, uploads

# ----------------------------------------------------
# 1. 라이프사이클 이벤트 (DB 초기화)
# ----------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    애플리케이션 시작(startup) 및 종료(shutdown) 시 실행되는 이벤트 핸들러입니다.
    """
    print("[APP STARTUP] Database initialization started...")
    # 서버 시작 시 DB 엔진을 초기화하고, 테이블이 없으면 생성합니다.
    # User, OTPVerificationRequest 테이블 등이 생성됩니다.
    database.create_db_and_tables()
    print("[APP STARTUP] Database initialized successfully.")
    
    # yield: 이 시점부터 FastAPI가 요청 처리를 시작합니다.
    yield
    
    # 서버 종료 시 (shutdown) 필요한 정리 작업은 여기에 추가합니다.
    print("[APP SHUTDOWN] Application shutdown complete.")


# ----------------------------------------------------
# 2. FastAPI 인스턴스 생성
# ----------------------------------------------------

# lifespan 이벤트 핸들러를 등록하여 DB 초기화 시점을 제어합니다.
app = FastAPI(
    title="Ilowa API (FastAPI Backend)",
    version="v1",
    description="시니어 구직자를 위한 AI 기반 일자리 추천 서비스 백엔드 API",
    lifespan=lifespan,
    # docs_url="/api/v1/docs" # 문서 경로를 /api/v1/docs로 설정할 수도 있습니다.
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ----------------------------------------------------
# 3. 미들웨어 설정 (CORS)
# ----------------------------------------------------

# 프론트엔드가 백엔드에 접근할 수 있도록 CORS를 설정합니다.
origins = [
    "http://localhost",
    "http://localhost:3000", # Next.js/React 프론트엔드 기본 포트
    "http://127.0.0.1:3000",
    # TODO: 프로덕션 환경의 실제 도메인 추가
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # 모든 HTTP 메서드 허용 (GET, POST, PATCH 등)
    allow_headers=["*"], # 모든 HTTP 헤더 허용 (Authorization 포함)
)


# ----------------------------------------------------
# 4. 라우터 등록 및 버전 관리
# ----------------------------------------------------

# v1 API 라우터들을 메인 애플리케이션에 등록합니다.
# prefix="/api/v1"을 사용하여 모든 엔드포인트가 /api/v1/...으로 시작하게 됩니다.
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])
app.include_router(users.router, prefix="/api/v1", tags=["User"])
app.include_router(applications.router, prefix="/api/v1", tags=["Applications"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])
app.include_router(matches.router, prefix="/api/v1", tags=["Matches"])
app.include_router(profile.router)
app.include_router(uploads.router)
app.include_router(ai.router)
app.include_router(notifications.router, prefix="/api/v1", tags=["Notifications"])

app.mount("/media", StaticFiles(directory="backend_api/app/storage"), name="media")


# ----------------------------------------------------
# 5. 서버 실행 (개발 환경용)
# ----------------------------------------------------

if __name__ == "__main__":
    # 개발 환경에서 서버를 구동하는 명령어입니다.
    # uvicorn backend_api.app.main:app --reload 와 동일하게 작동합니다.
    uvicorn.run(
        "backend_api.app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
    )
