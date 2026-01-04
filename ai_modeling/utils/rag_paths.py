from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_RAG_CSV = REPO_ROOT / "ai_modeling" / "data_samples" / "demo_jobs_50_with_embeddings.csv"
LEGACY_RAG_CSV = REPO_ROOT / "ai_modeling" / "data" / "new_work_with_embeddings.csv"


def _resolve_env_path(raw_value: Optional[str], default_name: str) -> Optional[Path]:
    if not raw_value:
        return None
    value = raw_value.strip()
    if not value:
        return None
    path = Path(value).expanduser()
    if path.suffix:
        return path
    return path / default_name


def resolve_rag_csv_path() -> Path:
    """Resolve the CSV path for RAG (CSV + embedding)."""
    for env_name in ("RAG_DATA_PATH", "SEED_PATH", "DATA_DIR"):
        candidate = _resolve_env_path(os.getenv(env_name), DEMO_RAG_CSV.name)
        if not candidate:
            continue
        if candidate.suffix.lower() != ".csv":
            continue
        return candidate

    if DEMO_RAG_CSV.exists():
        return DEMO_RAG_CSV
    return LEGACY_RAG_CSV
