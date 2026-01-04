from __future__ import annotations

import logging
import os
import tempfile
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from pathlib import Path

logger = logging.getLogger(__name__)

from ai_modeling.agents.posting_agent import PostingAutomationAgent
from ai_modeling.agents.react_agent import ReActAgent
from ai_modeling.services.providers import get_ai_provider
from ai_modeling.utils.rag_paths import resolve_rag_csv_path

BASE_DIR = Path(__file__).resolve().parent.parent

# def _resolve_default_csv_path() -> str:
#     """Pick the embedding CSV path honoring environment overrides."""

#     env_candidates = [
#         ("AI_RECOMMENDER_CSV", os.getenv("AI_RECOMMENDER_CSV")),
#         ("RECOMMENDER_JOBS_CSV", os.getenv("RECOMMENDER_JOBS_CSV")),
#         ("AI_EMBEDDING_CSV", os.getenv("AI_EMBEDDING_CSV")),
#         ("SEED_JOBS_JSON", os.getenv("SEED_JOBS_JSON")),
#         ("SEED_JOBS_CSV", os.getenv("SEED_JOBS_CSV")),
#     ]
#     for env_name, raw_path in env_candidates:
#         candidate = (raw_path or "").strip()
#         if not candidate:
#             continue

#         resolved = Path(candidate).expanduser()
#         if resolved.suffix.lower() != ".csv":
#             logger.debug(
#                 "Skipping %s for AI recommender CSV because it is not a CSV file (value=%s)",
#                 env_name,
#                 candidate,
#             )
#             continue

#         return str(resolved)
#     return str(BASE_DIR / "data" / "new_work_with_embeddings.csv")

def _resolve_default_csv_path() -> str:
    """Pick the CSV path for RAG (CSV + embedding)."""

    resolved = resolve_rag_csv_path()
    print(f"[AI] Using recommender CSV: {resolved}")
    return str(resolved)

DEFAULT_CSV_PATH = _resolve_default_csv_path()


def _normalize_provider_name(name: Optional[str]) -> str:
    value = name or os.getenv("AI_PROVIDER") or "naver"
    return value.strip().lower().replace("-", "_")


class AIModelingOrchestrator:
    """
    High-level orchestrator that wires together recommendation and posting agents.

    The orchestrator is provider-aware so we can swap out Naver Cloud today and
    move to a fine-tuned open model tomorrow without changing call sites.
    """

    def __init__(self, provider_name: Optional[str] = None, csv_path: str = DEFAULT_CSV_PATH):
        normalized = _normalize_provider_name(provider_name)
        self._provider = get_ai_provider(normalized)
        self.provider_name = getattr(self._provider, "name", normalized)
        self.csv_path = csv_path
        self._react_agent = ReActAgent(csv_path=csv_path, provider=self._provider)
        self._posting_agent = PostingAutomationAgent(provider=self._provider)

    def recommend(
        self,
        user_profile: Dict[str, Any],
        intent: str = "",
        previous_recommendations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        result = self._react_agent.run(
            user_profile=user_profile,
            intent=intent,
            previous_recommendations=previous_recommendations or [],
        )
        result["provider"] = self.provider_name
        return result

    def _run_voice_pipeline(self, audio_bytes: bytes, lang: str = "Kor") -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            return self._posting_agent.extract_from_voice(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def create_post_from_voice_bytes(self, audio_bytes: bytes, lang: str = "Kor") -> Dict[str, Any]:
        result = self._run_voice_pipeline(audio_bytes, lang=lang)
        result["provider"] = self.provider_name
        return result

    def create_post_from_image_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        result = self._posting_agent.extract_from_image_bytes(image_bytes)
        result["provider"] = self.provider_name
        return result

    def create_post_from_text(self, raw_text: str) -> Dict[str, Any]:
        result = self._posting_agent.extract_from_text(raw_text)
        result["provider"] = self.provider_name
        return result

    def validate_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a structured post and surface missing fields/questions."""
        return self._posting_agent.check_missing_fields(post)

    def transcribe_audio_file(self, file_path: str, lang: str = "Kor") -> Dict[str, Any]:
        """Use the underlying provider STT directly (for media already on disk)."""
        return self._provider.transcribe_audio(file_path, lang=lang)

    def describe(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "csv_path": self.csv_path,
        }

    def merge_post_with_text(self, post: Dict[str, Any], additional_text: str) -> Dict[str, Any]:
        """Merge clarification text into an existing structured post."""
        return self._posting_agent.merge_additional_input(post, additional_text)

    def normalize_address(self, address_text: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Use the LLM to convert fuzzy address descriptions into geocodable text."""
        try:
            return self._posting_agent.normalize_address(address_text, context=context or {})
        except Exception:
            return None


@lru_cache(maxsize=4)
def get_orchestrator(provider_name: Optional[str] = None) -> AIModelingOrchestrator:
    normalized = _normalize_provider_name(provider_name)
    return AIModelingOrchestrator(provider_name=normalized)
