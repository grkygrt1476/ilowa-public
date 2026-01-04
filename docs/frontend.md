# Frontend Deep Dive (Portfolio Snapshot)

The frontend is a lightweight React UI used to demonstrate the flows in this public
snapshot. Details are kept minimal in the root README; this page summarizes the UI
surface without introducing new dependencies.

## User flows (high-level)
- Browse and search job posts.
- View job details.
- Optional assisted posting via OCR/STT (when backend endpoints are enabled).
- Optional recommendation flow (when enabled by the backend).

## Screens and routing (summary)
- TODO: list actual routes/screens based on the current React router config.
- TODO: note which screens integrate OCR/STT inputs vs. standard form inputs.

## Local run
```bash
cd frontend_app
npm install  # if needed
npm start    # macOS/Linux
# Windows: npm run dev
```

Open http://localhost:3000

## Configuration
- Local settings live in `frontend_app/.env` (no secrets should be committed).
- Point the API base URL to the backend (default demo port is 18000).
