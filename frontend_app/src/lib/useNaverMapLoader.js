import { useEffect, useState } from "react";

export default function useNaverMapLoader(options = { submodules: ["geocoder"] }) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.naver && window.naver.maps) {
      setLoaded(true);
      return;
    }

    const clientId = process.env.REACT_APP_NAVER_MAP_CLIENT_ID;
    if (!clientId) {
      setError("NAVER MAP Client ID가 설정되지 않았습니다 (.env 확인).");
      return;
    }

    const existed = document.getElementById("naver-map-sdk");
    if (existed) {
      existed.addEventListener("load", () => setLoaded(true), { once: true });
      existed.addEventListener("error", () => setError("네이버 지도 스크립트 로드 실패"), { once: true });
      return;
    }

    // ✅ 최신 버전: oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=...
    const script = document.createElement("script");
    const sub = (options.submodules || []).join(",");
    script.id = "naver-map-sdk";
    script.async = true;
    script.defer = true;
    script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${clientId}${
      sub ? `&submodules=${sub}` : ""
    }`;

    script.onload = () => setLoaded(true);
    script.onerror = () => setError("네이버 지도 스크립트 로드 실패");
    document.head.appendChild(script);
  }, [options.submodules]);

  return { loaded, error };
}