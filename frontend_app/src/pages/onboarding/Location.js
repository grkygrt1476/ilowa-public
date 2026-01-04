import React, { useMemo, useState } from "react";
import { ChevronLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

const runtimeEnv =
  typeof window !== "undefined" ? window.__ENV || window.__env || {} : {};

const getEnvValue = (...keys) => {
  for (const key of keys) {
    if (!key) continue;
    const fromProcess = process.env[key];
    if (typeof fromProcess === "string" && fromProcess.length > 0) {
      return fromProcess;
    }
    if (
      runtimeEnv &&
      typeof runtimeEnv[key] === "string" &&
      runtimeEnv[key].length > 0
    ) {
      return runtimeEnv[key];
    }
  }
  return undefined;
};

const boolFromEnv = (value) => {
  if (!value) return false;
  const normalized = value.trim().toLowerCase();
  return ["1", "true", "yes", "y"].includes(normalized);
};

const parseCoordinatePair = (latStr, lngStr) => {
  const lat = Number.parseFloat(latStr);
  const lng = Number.parseFloat(lngStr);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lat, lng };
};

const parseTupleCoord = (value) => {
  if (!value) return null;
  const cleaned = value
    .replaceAll("(", "")
    .replaceAll(")", "")
    .replaceAll("[", "")
    .replaceAll("]", "")
    .trim();
  const parts = cleaned.split(/[,\\s]+/).filter(Boolean);
  if (parts.length < 2) return null;
  return parseCoordinatePair(parts[0], parts[1]);
};

const BASE_URL =
  getEnvValue("REACT_APP_API_BASE_URL", "API_BASE_URL", "base_url") ||
  "http://127.0.0.1:8000";
const cordFixedEnv = getEnvValue(
  "REACT_APP_CORD_FIXED",
  "REACT_APP_cord_fixed",
  "cord_fixed",
  "CORD_FIXED"
);
const IS_CORD_FIXED = boolFromEnv(cordFixedEnv);

const latEnv = getEnvValue(
  "REACT_APP_NIA_CORD_Y",
  "REACT_APP_nia_cord_y",
  "REACT_APP_NIA_LAT",
  "NIA_CORD_Y",
  "NIA_cord_y"
);
const lngEnv = getEnvValue(
  "REACT_APP_NIA_CORD_X",
  "REACT_APP_nia_cord_x",
  "REACT_APP_NIA_LNG",
  "NIA_CORD_X",
  "NIA_cord_x"
);
const tupleCoord = getEnvValue(
  "REACT_APP_NIA_CORD",
  "REACT_APP_nia_cord",
  "NIA_CORD",
  "NIA_cord",
  "nia_cord"
);

const FIXED_COORD =
  (latEnv && lngEnv && parseCoordinatePair(latEnv, lngEnv)) ||
  parseTupleCoord(tupleCoord);
if (process.env.NODE_ENV !== "production") {
  // eslint-disable-next-line no-console
  console.info(
    "[Location] cord_fixed:",
    IS_CORD_FIXED,
    "coord:",
    FIXED_COORD,
    "API:",
    getEnvValue("REACT_APP_API_BASE_URL", "API_BASE_URL", "base_url")
  );
}

const REGION_COORDS = {
  성동구: { lat: 37.5636, lng: 127.0364 },
  광진구: { lat: 37.5386, lng: 127.0826 },
  강남구: { lat: 37.5172, lng: 127.0473 },
  서초구: { lat: 37.4836, lng: 127.0327 },
  송파구: { lat: 37.5145, lng: 127.1056 },
  강동구: { lat: 37.5301, lng: 127.1238 },
  마포구: { lat: 37.5663, lng: 126.9018 },
  용산구: { lat: 37.5311, lng: 126.981 },
  중구: { lat: 37.5636, lng: 126.9978 },
  종로구: { lat: 37.5735, lng: 126.9794 },
  동대문구: { lat: 37.5744, lng: 127.0396 },
  중랑구: { lat: 37.5986, lng: 127.0927 },
};

const findNearestRegion = (lat, lng, coordsMap = REGION_COORDS) => {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return "";
  let nearest = "";
  let minDist = Infinity;
  Object.entries(coordsMap).forEach(([name, coord]) => {
    const dLat = lat - coord.lat;
    const dLng = lng - coord.lng;
    const dist = dLat * dLat + dLng * dLng;
    if (dist < minDist) {
      minDist = dist;
      nearest = name;
    }
  });
  return nearest;
};

const getToken = () =>
  (typeof window !== "undefined" ? localStorage.getItem("access_token") : null) || "";

export default function Location({ onPrev }) {
  const nav = useNavigate();
  const regionCoords = useMemo(() => REGION_COORDS, []);
  const regions = useMemo(() => Object.keys(REGION_COORDS), []);
  const nearestFixedRegion = useMemo(() => {
    if (IS_CORD_FIXED && FIXED_COORD) {
      return findNearestRegion(
        FIXED_COORD.lat,
        FIXED_COORD.lng,
        regionCoords
      );
    }
    return "";
  }, [regionCoords]);

  const [useGPS, setUseGPS] = useState(Boolean(nearestFixedRegion));
  const [selectedRegion, setSelectedRegion] = useState(nearestFixedRegion);
  const [saving, setSaving] = useState(false);
  const [geoStatus, setGeoStatus] = useState(
    nearestFixedRegion ? "시연 좌표 기준으로 자동 설정했어요." : ""
  );
  const [geoLoading, setGeoLoading] = useState(false);

  /** ✅ 위치 저장 (닉네임처럼 save 함수 분리) */
  const save = async () => {
    const token = getToken();
    if (!token) return alert("로그인 토큰이 없습니다.");
    if (!selectedRegion) return alert("선호 지역을 먼저 선택해주세요.");

    try {
      setSaving(true);
      const res = await fetch(`${BASE_URL}/profile/prefs/location`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          use_gps: useGPS,
          regions: selectedRegion ? [selectedRegion] : [],
        }),
      });

      if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
    } catch (err) {
      alert(err.message);
      throw err; // handleSkip 실행 방지
    } finally {
      setSaving(false);
      nav("/onboarding/time", { replace: true });
    }
  };
  const handleSkip = () => {
    // 건너뛰기 처리 - 다음 단계로 이동하거나 홈으로 이동
    nav("/onboarding/time", { replace: true });
  };

  const handleGpsClick = () => {
    if (IS_CORD_FIXED && FIXED_COORD) {
      const nearest = findNearestRegion(
        FIXED_COORD.lat,
        FIXED_COORD.lng,
        regionCoords
      );
      if (nearest) {
        setSelectedRegion(nearest);
        setGeoStatus("시연 좌표 기준으로 자동 설정했어요.");
        setUseGPS(true);
      }
      return;
    }

    if (!navigator.geolocation) {
      alert("위치 정보를 사용할 수 없습니다.");
      return;
    }
    if (useGPS) {
      setUseGPS(false);
      setSelectedRegion("");
      setGeoStatus("");
      return;
    }
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setGeoLoading(false);
        const nearest = findNearestRegion(
          coords.latitude,
          coords.longitude,
          regionCoords
        );
        if (nearest) {
          setSelectedRegion(nearest);
          setGeoStatus(`${nearest} 기준으로 자동 설정했어요.`);
          setUseGPS(true);
        } else {
          alert("현재 위치로 선호 지역을 찾지 못했어요. 직접 선택해주세요.");
        }
      },
      (err) => {
        console.error(err);
        setGeoLoading(false);
        alert("위치 정보를 가져오지 못했습니다. 권한을 허용했는지 확인해주세요.");
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* 헤더 */}
        <header className="px-6 py-7 flex items-center justify-between border-b">
          <button
            type="button"
            className="p-2"
            onClick={() => (onPrev ? onPrev() : nav(-1))}
          >
            <ChevronLeft className="w-6 h-6" />
          </button>

          {/* ✅ 가운데 정렬된 제목 */}
          <h1 className="absolute left-1/2 -translate-x-1/2 text-xl font-bold">
            선호 위치 선택
          </h1>

          <div className="w-10" />
          <button 
            onClick={handleSkip}
            className="text-black font-medium text-sm"
          >
            건너뛰기
          </button>
        </header>

      {/* 본문 */}
      <main className="flex-1 px-6 py-8">
        <h2 className="text-3xl font-bold mb-3">
          어느 지역에서
          <br />
          일하고 싶으신가요?
        </h2>
        <p className="text-gray-600 text-lg mb-8">
          가까운 곳의 일자리를 추천해드려요
        </p>

        {/* GPS 버튼 */}
        <div className="mb-6">
          <button
            type="button"
            onClick={handleGpsClick}
            className={`w-full p-4 rounded-xl border-2 flex items-center justify-between
                        bg-white text-gray-800 focus:outline-none transition
                        ${
                          useGPS
                            ? "border-orange-500 bg-orange-500/10"
                            : "border-gray-300"
                        }`}
          >
            <span className="font-medium text-lg">현재 위치 기반 자동 설정</span>
            <div
              className={`w-6 h-6 rounded-full border-2 transition-colors duration-150 ${
                useGPS
                  ? "bg-orange-500 border-orange-500/10"
                  : "border-gray-300 bg-white"
              }`}
            />
          </button>
          {geoLoading && (
            <p className="text-xs text-gray-500 mt-2">현재 위치를 확인하는 중입니다…</p>
          )}
          {geoStatus && !geoLoading && (
            <p className="text-xs text-emerald-600 mt-2">{geoStatus}</p>
          )}
        </div>

        {/* 자치구 버튼 */}
        <h3 className="font-bold text-lg mb-3">또는 직접 선택</h3>
        <div className="grid grid-cols-3 gap-3">
          {regions.map((region) => {
            const isSelected = selectedRegion === region;
            return (
              <button
                key={region}
                type="button"
                onClick={() => {
                  setSelectedRegion(region);
                  setUseGPS(false);
                }}
                className={`py-3 px-4 rounded-lg border-2 font-medium transition
                            focus:outline-none
                            ${
                              isSelected
                                ? "border-orange-500 bg-orange-500/10 text-black-600"
                                : "border-gray-300 bg-white text-gray-800 hover:border-gray-400"
                            }`}
              >
                {region}
              </button>
            );
          })}
        </div>
      </main>

      {/* 하단 버튼 */}
      <footer className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 py-4 z-40">
        <div className="max-w-7xl mx-auto px-4">
          <button
            type="button"
            onClick={async () => {
              await save();   // ✅ 저장 먼저
              handleSkip();   // ✅ 저장 완료 후 이동
            }}
            disabled={saving || !selectedRegion}
            className={`w-full font-bold text-xl py-5 rounded-xl transition
              ${
                !selectedRegion
                  ? "bg-orange-300 text-white cursor-not-allowed"
                  : "bg-orange-500 text-white hover:bg-orange-600"
              }`}
          >
            {saving ? "저장 중..." : "다음"}
          </button>
        </div>
      </footer>
    </div>
  );
}
