from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, Optional, Type

from .base import AIProvider
from .local_stub import LocalFinetunedProvider
from .naver import NaverCloudProvider

_PROVIDER_REGISTRY: Dict[str, Type[AIProvider]] = {
    "naver": NaverCloudProvider,
    "naver_cloud": NaverCloudProvider,
    "clova": NaverCloudProvider,
    "local": LocalFinetunedProvider,
    "open": LocalFinetunedProvider,
    "finetuned": LocalFinetunedProvider,
}


def _normalize_name(name: Optional[str]) -> str:
    value = name or os.getenv("AI_PROVIDER") or "naver"
    return value.strip().lower().replace("-", "_")


@lru_cache(maxsize=8)
def _build_provider(name: str) -> AIProvider:
    if name not in _PROVIDER_REGISTRY:
        raise ValueError(f"지원하지 않는 AI Provider: {name}")
    provider_cls = _PROVIDER_REGISTRY[name]
    return provider_cls()


def get_ai_provider(name: Optional[str] = None) -> AIProvider:
    """Return (and cache) the provider instance for the requested name."""
    normalized = _normalize_name(name)
    return _build_provider(normalized)


def list_available_providers() -> Dict[str, str]:
    """Expose provider names and the backing class for debugging."""
    return {name: cls.__name__ for name, cls in _PROVIDER_REGISTRY.items()}
