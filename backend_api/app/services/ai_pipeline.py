"""Helpers to access the ai_modeling orchestrator from the backend API."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from ai_modeling.orchestration import AIModelingOrchestrator, get_orchestrator

from backend_api.app.core.config import settings


def _normalize_provider(name: Optional[str]) -> str:
    """Normalize provider names to align with ai_modeling conventions."""

    value = name or getattr(settings, "AI_PROVIDER", None) or "naver"
    return value.strip().lower().replace("-", "_")


@lru_cache(maxsize=4)
def _cached_orchestrator(provider_name: str) -> AIModelingOrchestrator:
    """Cache orchestrator instances per provider to avoid reloading CSV/LLM state."""

    return get_orchestrator(provider_name)


def get_pipeline(provider: Optional[str] = None) -> AIModelingOrchestrator:
    """Public accessor for routes/services."""

    normalized = _normalize_provider(provider)
    return _cached_orchestrator(normalized)
