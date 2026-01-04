from __future__ import annotations

from typing import Any, Dict, List

from ai_modeling.services.clova_embedding import get_clova_embedding
from ai_modeling.services.clova_llm import CompletionExecutor
from ai_modeling.services.clova_ocr import run_clova_ocr
from ai_modeling.services.clova_stt import clova_stt_from_file

from .base import AIProvider


class NaverCloudProvider(AIProvider):
    """Concrete provider that routes every capability to Naver Cloud (Clova) APIs."""

    name = "naver"

    def __init__(self):
        self._llm = CompletionExecutor()

    def generate_completion(self, completion_request: Dict[str, Any]) -> str:
        return self._llm.execute(completion_request)

    def embed_text(self, text: str) -> List[float]:
        return get_clova_embedding(text)

    def transcribe_audio(self, file_path: str, lang: str = "Kor") -> Dict[str, Any]:
        return clova_stt_from_file(file_path, lang=lang)

    def ocr_image(self, image_bytes: bytes) -> str:
        return run_clova_ocr(image_bytes)
