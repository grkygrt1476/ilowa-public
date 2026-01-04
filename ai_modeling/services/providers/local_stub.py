from __future__ import annotations

from typing import Any, Dict, List

from .base import AIProvider


class LocalFinetunedProvider(AIProvider):
    """
    Placeholder provider for future self-hosted / fine-tuned models.

    The implementation intentionally raises a RuntimeError so that the call site
    can decide whether to catch the error or fall back to another provider.
    """

    name = "local"

    def _raise(self) -> None:
        raise RuntimeError(
            "Local fine-tuned provider is not configured yet. "
            "Implement LocalFinetunedProvider or set AI_PROVIDER=naver."
        )

    def generate_completion(self, completion_request: Dict[str, Any]) -> str:
        self._raise()

    def embed_text(self, text: str) -> List[float]:
        self._raise()

    def transcribe_audio(self, file_path: str, lang: str = "Kor") -> Dict[str, Any]:
        self._raise()

    def ocr_image(self, image_bytes: bytes) -> str:
        self._raise()
