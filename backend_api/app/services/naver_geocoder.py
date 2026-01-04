from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests


class NaverGeocoder:
    """Thin wrapper around Naver Maps geocode API with simple disk cache."""

    API_URL = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        cache_path: Optional[Path] = None,
        rate_limit_sleep: float = 0.15,
    ) -> None:
        self.client_id = client_id or os.getenv("NAVER_MAPS_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NAVER_MAPS_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise RuntimeError("NAVER_MAPS_CLIENT_ID/SECRET must be set")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-NCP-APIGW-API-KEY-ID": self.client_id,
                "X-NCP-APIGW-API-KEY": self.client_secret,
            }
        )
        self.cache_path = cache_path or Path(".naver_geocode_cache.json")
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

    def geocode(self, query: str) -> Optional[Tuple[float, float]]:
        normalized = query.strip()
        if not normalized:
            return None
        if normalized in self.cache:
            return self.cache[normalized]

        resp = self.session.get(self.API_URL, params={"query": normalized})
        if resp.status_code != 200:
            print(f"[Geocoder] HTTP {resp.status_code}: {resp.text}")
            return None

        data = resp.json()
        addresses = data.get("addresses") or []
        if not addresses:
            return None

        best = addresses[0]
        lat = float(best["y"])
        lng = float(best["x"])
        self.cache[normalized] = (lat, lng)
        self._save_cache()
        time.sleep(self.rate_limit_sleep)
        return lat, lng
