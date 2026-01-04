from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AIProvider(ABC):
    """Abstract base class describing the capabilities an AI provider must expose."""

    name: str = "base"

    @abstractmethod
    def generate_completion(self, completion_request: Dict[str, Any]) -> str:
        """Execute a chat/completion style request and return the raw text response."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Return a vector embedding for the supplied text."""

    @abstractmethod
    def transcribe_audio(self, file_path: str, lang: str = "Kor") -> Dict[str, Any]:
        """Transcribe the audio file and return at least {'text': '...'}."""

    @abstractmethod
    def ocr_image(self, image_bytes: bytes) -> str:
        """Perform OCR on the supplied bytes and return HTML/text suitable for parsing."""
