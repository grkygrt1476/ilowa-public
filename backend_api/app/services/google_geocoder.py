from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import requests


class GoogleGeocoder:
    """Minimal wrapper around Google Geocoding API with a small disk cache."""

    API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_path: Optional[Path] = None,
        rate_limit_sleep: float = 0.1,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("GOOGLE_GEOCODING_API_KEY")
            or os.getenv("GOOGLE_GEOCODING")
        )
        if not self.api_key:
            raise RuntimeError("GOOGLE_GEOCODING_API_KEY (or GOOGLE_GEOCODING) must be set")

        self.session = requests.Session()
        self.cache_path = cache_path or Path(".google_geocode_cache.json")
        self.rate_limit_sleep = rate_limit_sleep
        self.cache: Dict[str, Tuple[float, float]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            try:
                with self.cache_path.open("r", encoding="utf-8") as fp:
                    raw = json.load(fp)
                self.cache = {k: tuple(v) for k, v in raw.items()}
            except Exception:
                self.cache = {}

    def _save_cache(self) -> None:
        try:
            with self.cache_path.open("w", encoding="utf-8") as fp:
                json.dump(self.cache, fp, ensure_ascii=False)
        except Exception:
            pass

    def geocode(
        self,
        query: str,
        *,
        return_details: bool = False,
    ) -> Optional[Union[Tuple[float, float], Tuple[float, float, Optional[str]]]]:
        normalized = query.strip()
        if not normalized:
            return None
        if normalized in self.cache:
            coords = self.cache[normalized]
            if return_details:
                lat, lng = coords
                return lat, lng, None
            return coords

        resp = self.session.get(
            self.API_URL,
            params={
                "address": normalized,
                "key": self.api_key,
                "language": "ko",
            },
        )
        if resp.status_code != 200:
            print(f"[GoogleGeocoder] HTTP {resp.status_code}: {resp.text}")
            return None

        data = resp.json()
        if data.get("status") != "OK":
            print(f"[GoogleGeocoder] status={data.get('status')} error={data.get('error_message')}")
            return None

        results = data.get("results") or []
        if not results:
            return None

        top = results[0]
        geometry = top.get("geometry", {})
        location = geometry.get("location")
        if not location:
            return None

        lat = float(location.get("lat"))
        lng = float(location.get("lng"))
        self.cache[normalized] = (lat, lng)
        self._save_cache()
        time.sleep(self.rate_limit_sleep)
        if return_details:
            formatted = (top.get("formatted_address") or "").strip() or None
            return lat, lng, formatted
        return lat, lng
