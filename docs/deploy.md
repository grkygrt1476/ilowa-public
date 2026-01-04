# Deployment Deep Dive (Portfolio Snapshot)

This page captures the deployment view for the public snapshot.
The diagram shows how the local demo/cleanroom setup maps containers and external APIs.
It does not include production secrets or credentials.

## Deployment Architecture (Local Demo / Cleanroom)
```mermaid
flowchart LR
  subgraph Client
    C["웹 브라우저(PC/모바일)<br/>(React 웹앱 사용)"]
  end

  subgraph DNS["DNS (Naver Cloud DNS, 인프라 외부)"]
    DNS_A["ilowa.site A 레코드<br/>→ 49.50.---.---"]
  end

  subgraph Server["애플리케이션 서버 (단일 VM/호스트)"]
    subgraph Compose["Docker Compose (server 브랜치 런타임)"]
      API["api 컨테이너<br/>(FastAPI 백엔드)"]
      DB["db 컨테이너<br/>(PostgreSQL + PostGIS + pgvector)"]
    end
    MEDIA["로컬 스토리지<br/>backend_api/app/storage → /media"]
  end

  subgraph External["외부 API / AI (선택적 사용)"]
    GEO["Naver/Google 지오코더<br/>(주소→좌표 변환 등)"]
    LLM["Clova / OpenAI LLM<br/>(키 설정 시만 호출)"]
  end

  C --> DNS_A --> API

  API --> DB
  DB --> API

  API --> MEDIA

  API --> GEO
  API --> LLM
```

## Local Demo Notes
- Docker Compose runs the api/db containers for local demo and cleanroom runs.
- Published ports default to API 18000 and DB 15432 (override via env).
- Internal DB connections use `db:5432`.
- Cleanroom routine is described in the README.
