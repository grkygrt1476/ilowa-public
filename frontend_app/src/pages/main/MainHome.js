// src/pages/main/MainHome.js
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useNavigate, useLocation } from "react-router-dom";
import TopBar from "../../components/TopBar";
import BottomNav from "../../components/BottomNav";
import useNaverMapLoader from "../../lib/useNaverMapLoader";
import {
  ApiError,
  JobsAPI,
  UsersAPI,
  apiFetch,
  parseApiError,
  toCurrency,
  MediaAPI,
  AIAPI,
  ApplicationsAPI,
} from "../../utils/apiClient";
import { Mic, PenLine } from "lucide-react";

const MAX_NEARBY_JOBS = 100;

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
  const parts = cleaned.split(/[ \s]+/).filter(Boolean);
  if (parts.length < 2) return null;
  return parseCoordinatePair(parts[0], parts[1]);
};

const boolFromEnv = (value) => {
  if (!value) return false;
  const normalized = value.trim().toLowerCase();
  return ["1", "true", "yes", "y"].includes(normalized);
};

const cordFixedEnv = getEnvValue(
  "REACT_APP_CORD_FIXED",
  "REACT_APP_cord_fixed",
  "cord_fixed"
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

const FIXED_COORD =
  parseCoordinatePair(latEnv, lngEnv) ||
  parseTupleCoord(
    getEnvValue(
      "REACT_APP_NIA_CORD",
      "REACT_APP_nia_cord",
      "NIA_CORD",
      "nia_cord"
    )
  );
if (process.env.NODE_ENV !== "production") {
  // eslint-disable-next-line no-console
  console.info("[MainHome] cord_fixed:", IS_CORD_FIXED, "coord:", FIXED_COORD, "API:", process.env.REACT_APP_API_BASE_URL || runtimeEnv.REACT_APP_API_BASE_URL);
}
const haversineDistance = (lat1, lng1, lat2, lng2) => {
  const toRad = (deg) => (deg * Math.PI) / 180;
  const R = 6371000; // meters
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

const parseMoneyValue = (value) => {
  if (value == null || value === "") return null;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const digits = String(value).replace(/[^\d.]/g, "");
  if (!digits) return null;
  const num = Number.parseFloat(digits);
  if (Number.isNaN(num)) return null;
  return num;
};

const AIResultCard = ({ job }) => {
  const place = job.place || job.location || job.address || job.region || "";
  const wageText =
    job.pay_text ||
    (job.hourly_wage != null ? `시급 ${toCurrency(job.hourly_wage)}` : "협의");
  const description = job.description || job.client || "";
  const reason =
    job.recommendation_reason || "AI가 프로필과 잘 맞다고 판단했어요.";

  return (
    <div className="bg-white/95 border border-orange-100 rounded-2xl shadow-xl p-4">
      <p className="text-xs font-semibold text-orange-500 mb-1">AI 추천</p>
      <h3 className="text-lg font-bold text-gray-900">
        {job.title || "추천 공고"}
      </h3>
      <p className="text-sm text-gray-600 mt-1">
        📍 {place || "위치 정보 없음"}
      </p>
      <p className="text-sm text-gray-600">💰 {wageText}</p>
      {description ? (
        <p className="text-sm text-gray-500 mt-2">{description}</p>
      ) : null}
      <p className="text-sm text-emerald-700 font-semibold mt-3">
        추천 이유: {reason}
      </p>
    </div>
  );
};

export default function MainHome() {
  const navigate = useNavigate();
  const location = useLocation();

  const normalizeJob = (job) => {
    if (!job) return null;

    const rawLat =
      job.lat ??
      job.latitude ??
      job.location_latitude ??
      job.coords?.lat ??
      job.position?.lat;
    const rawLng =
      job.lng ??
      job.longitude ??
      job.location_longitude ??
      job.coords?.lng ??
      job.position?.lng;

    const lat = rawLat != null ? Number(rawLat) : Number.NaN;
    const lng = rawLng != null ? Number(rawLng) : Number.NaN;

    const hourlyValue = parseMoneyValue(job.hourly_wage ?? job.hourlyWage);
    const payValue = parseMoneyValue(job.pay ?? job.wage);
    const payText =
      job.pay_text ?? job.wage_text ?? job.salary_text ?? job.wage ?? job.pay;
    const workDays = Array.isArray(job.work_days)
      ? job.work_days
      : Array.isArray(job.workDays)
      ? job.workDays
      : [];
    const startTime =
      job.start_time ??
      job.startTime ??
      job.shift_start ??
      job.schedule_start ??
      null;
    const endTime =
      job.end_time ??
      job.endTime ??
      job.shift_end ??
      job.schedule_end ??
      null;
    const baseShift = job.schedule || job.time || job.shift;
    let shift = baseShift;
    if (!shift && startTime && endTime) {
      shift = `${startTime} ~ ${endTime}`;
    }
    if (!shift && workDays.length) {
      shift = workDays.join(", ");
    }
    if (!shift) {
      shift = "시간 미정";
    }

    let wageDisplay = payText || "협의";
    if (hourlyValue != null) {
      wageDisplay = `시급 ${toCurrency(hourlyValue)}`;
    } else if (payValue != null) {
      wageDisplay = `시급 ${toCurrency(payValue)}`;
    }

    return {
      id: job.id,
      title: job.title || "공고",
      location: job.place || job.location || job.address || "",
      wage: wageDisplay,
      shift,
      lat,
      lng,
      workDays,
      startTime,
      endTime,
      source: job.source ?? job.origin ?? null,
      raw: job,
    };
  };

  const [me, setMe] = useState(null);
  const [err, setErr] = useState("");
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [, setJobsLoading] = useState(true);
  const [jobErr, setJobErr] = useState("");
  const [myPos, setMyPos] = useState(() =>
    IS_CORD_FIXED && FIXED_COORD ? { ...FIXED_COORD } : null
  );

  const baseJobs = useMemo(
    () => [
      {
        id: 1,
        title: "아파트 경비",
        location: "성동구",
        wage: "시급 12,000원",
        shift: "주간",
        lat: 37.5636,
        lng: 127.0372,
      },
      {
        id: 2,
        title: "빌딩 청소",
        location: "강남구",
        wage: "시급 13,000원",
        shift: "야간",
        lat: 37.4979,
        lng: 127.0276,
      },
      {
        id: 3,
        title: "주차관리",
        location: "송파구",
        wage: "시급 11,500원",
        shift: "주간",
        lat: 37.5145,
        lng: 127.1059,
      },
    ],
    []
  );
  const [displayJobs, setDisplayJobs] = useState(baseJobs);

  const [aiMode, setAiMode] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResults, setAiResults] = useState([]);
  const [selectedAiResult, setSelectedAiResult] = useState(null);
  const [aiOverlayOpen, setAiOverlayOpen] = useState(false);
  const [lastAiResults, setLastAiResults] = useState(() => {
    if (typeof window === "undefined") return null;
    try {
      const raw = window.localStorage.getItem("last_ai_recommendations");
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : null;
    } catch (e) {
      console.error("AI history parse failed", e);
      return null;
    }
  });
  const [aiDetailLoading, setAiDetailLoading] = useState(false);
  const [selectedAiDetail, setSelectedAiDetail] = useState(null);
  const [aiIntent, setAiIntent] = useState("");
  const [aiCoords, setAiCoords] = useState([]);

  const { loaded, error: mapError } = useNaverMapLoader({
    submodules: ["geocoder"],
  });

  const mapBoxRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const aiHighlightRef = useRef(null);
  const aiVoiceRecorderRef = useRef(null);
  const aiVoiceChunksRef = useRef([]);
  const [mapReady, setMapReady] = useState(false);
  const [isVoiceRecording, setIsVoiceRecording] = useState(false);
  const [aiFeedbackLoading, setAiFeedbackLoading] = useState(false);
  const [aiFeedbackError, setAiFeedbackError] = useState("");
  const [showTextFeedback, setShowTextFeedback] = useState(false);
  const [textFeedback, setTextFeedback] = useState("");
  const [aiApplyTarget, setAiApplyTarget] = useState(null);
  const [aiApplyNote, setAiApplyNote] = useState("잘 부탁드립니다.");
  const [aiApplyError, setAiApplyError] = useState("");
  const [aiApplySubmitting, setAiApplySubmitting] = useState(false);
  const [pendingCenterOnUser, setPendingCenterOnUser] = useState(false);

  const focusMapToCoords = (lat, lng) => {
    if (
      mapRef.current &&
      Number.isFinite(lat) &&
      Number.isFinite(lng) &&
      window.naver?.maps
    ) {
      const { naver } = window;
      const center = new naver.maps.LatLng(lat, lng);
      mapRef.current.setCenter(center);
      mapRef.current.setZoom(17);
      if (!aiHighlightRef.current) {
        aiHighlightRef.current = new naver.maps.Marker({
          position: center,
          map: mapRef.current,
          zIndex: 9999,
          icon: {
            content: `
              <div style="transform: translate(-50%, -100%); position: relative;">
                <div style="
                  background: #ffedd5;
                  border: 3px solid #fb923c;
                  padding: 8px 18px;
                  border-radius: 999px;
                  font-weight: 800;
                  color: #9a3412;
                  font-size: 14px;
                  white-space: nowrap;
                  box-shadow: 0 6px 16px rgba(251,146,60,0.4);
                ">AI 추천</div>
                <div style="
                  width: 0; height: 0;
                  border-left: 10px solid transparent;
                  border-right: 10px solid transparent;
                  border-top: 12px solid #fb923c;
                  margin: 0 auto; margin-top: -1px;
                "></div>
              </div>
            `,
          },
        });
      } else {
        aiHighlightRef.current.setPosition(center);
        aiHighlightRef.current.setMap(mapRef.current);
      }
    }
  };

  // 1) 사용자 정보
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      navigate("/", { replace: true });
      return;
    }

    UsersAPI.me()
      .then(setMe)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) {
          setErr("세션이 만료되었습니다. 다시 로그인해주세요.");
          setTimeout(() => navigate("/login", { replace: true }), 800);
        } else {
          setErr(parseApiError(e));
        }
      });
  }, [navigate]);

  // 2) 주변 소일거리
  useEffect(() => {
    let active = true;
    setJobsLoading(true);
    setJobErr("");

    const query = { page: 1, per_page: 100 };
    if (
      myPos &&
      Number.isFinite(myPos.lat) &&
      Number.isFinite(myPos.lng)
    ) {
      query.near_lat = myPos.lat;
      query.near_lng = myPos.lng;
    }

    JobsAPI.list(query)
      .then((data) => {
        if (!active) return;
        const items = Array.isArray(data) ? data : data?.items || [];
        const normalized = items.map((job) => normalizeJob(job)).filter(Boolean);
        setJobs(normalized);
      })
      .catch((e) => {
        if (!active) return;
        setJobErr(parseApiError(e, "주변 공고를 불러오는 중 문제가 발생했어요."));
      })
      .finally(() => {
        if (active) setJobsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [location.key, myPos]);

  // 3) 기본/AI 표시 데이터 동기화
  const jobsNearUser = useMemo(() => {
    if (!jobs?.length) return [];
    const hasMyPos =
      myPos &&
      Number.isFinite(myPos.lat) &&
      Number.isFinite(myPos.lng);
    if (!hasMyPos) {
      return jobs.slice(0, MAX_NEARBY_JOBS);
    }
    const withDistance = jobs.map((job) => {
      const validCoords =
        Number.isFinite(job.lat) && Number.isFinite(job.lng);
      const distance = validCoords
        ? haversineDistance(myPos.lat, myPos.lng, job.lat, job.lng)
        : Number.POSITIVE_INFINITY;
      return { ...job, distance };
    });
    withDistance.sort((a, b) => a.distance - b.distance);
    return withDistance.slice(0, MAX_NEARBY_JOBS);
  }, [jobs, myPos]);

  useEffect(() => {
    if (aiMode) return;
    if (jobsNearUser.length > 0) {
      setDisplayJobs(jobsNearUser);
    } else if (jobs.length > 0) {
      setDisplayJobs(jobs);
    } else {
      setDisplayJobs(baseJobs);
    }
  }, [jobsNearUser, jobs, aiMode, baseJobs]);

  // 4) 지도 생성
  useEffect(() => {
    if (!loaded || !mapBoxRef.current || mapRef.current) return;

    const { naver } = window;
    const initialCenter =
      IS_CORD_FIXED && FIXED_COORD
        ? new naver.maps.LatLng(FIXED_COORD.lat, FIXED_COORD.lng)
        : new naver.maps.LatLng(37.3595704, 127.105399);

    mapRef.current = new naver.maps.Map(mapBoxRef.current, {
      center: initialCenter,
      zoom: 10,
    });

    setMapReady(true);
  }, [loaded]);

  // 5) 마커 + 인포윈도우 렌더링
  const markerDataList = useMemo(() => {
    const numericJobs = displayJobs
      .map((j) => {
        const lat =
          typeof j.lat === "string"
            ? Number.parseFloat(j.lat)
            : typeof j.lat === "number"
            ? j.lat
            : Number.NaN;
        const lng =
          typeof j.lng === "string"
            ? Number.parseFloat(j.lng)
            : typeof j.lng === "number"
            ? j.lng
            : Number.NaN;
        return { ...j, lat, lng };
      })
      .filter((j) => {
        const ok = Number.isFinite(j.lat) && Number.isFinite(j.lng);
        if (!ok) {
          console.warn("[MainHome] Dropping job without coords", {
            id: j.id,
            title: j.title,
            lat: j.lat,
            lng: j.lng,
          });
        }
        return ok;
      });

    const groups = new Map();
    numericJobs.forEach((job) => {
      const key = `${job.lat.toFixed(5)},${job.lng.toFixed(5)}`;
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key).push(job);
    });

    const spreadMarkers = [];
    const radius = 0.0003;
    groups.forEach((group) => {
      if (group.length === 1) {
        spreadMarkers.push(group[0]);
        return;
      }
      group.forEach((job, idx) => {
        const angle = (2 * Math.PI * idx) / group.length;
        spreadMarkers.push({
          ...job,
          lat: job.lat + radius * Math.cos(angle),
          lng: job.lng + radius * Math.sin(angle),
        });
      });
    });

    return spreadMarkers.map((j) => ({
      ...j,
      html: `
            <div style="padding: 15px; min-width: 200px;">
              <h4 style="margin: 0 0 8px 0; font-size: 16px; font-weight: bold;">${j.title}</h4>
              <p style="margin: 4px 0; color: #666; font-size: 14px;">📍 ${j.location}</p>
              <p style="margin: 4px 0; color: ${j.shift === "야간" ? "#4B5563" : "#666"}; font-size: 14px;">⏰ ${j.shift}</p>
              <p style="margin: 4px 0; color: #FF6B35; font-weight: bold; font-size: 14px;">${j.wage}</p>
              <button 
                onclick="window.location.href='/jobs/${j.id}'"
                style="display:inline-block;margin-top:8px;padding:6px 10px;border:1px solid #ddd;border-radius:8px;background:#fff;cursor:pointer;text-decoration:none;color:#111;font-size:14px;">
                상세 보기
              </button>
            </div>
          `,
    }));
  }, [displayJobs]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    const { naver } = window;

    markersRef.current.forEach(({ marker }) => marker?.setMap(null));
    markersRef.current = [];

    markerDataList.forEach((job) => {
      const marker = new naver.maps.Marker({
        position: new naver.maps.LatLng(job.lat, job.lng),
        map: mapRef.current,
        title: job.title,
        icon: {
          content: `
            <div style="transform: translate(-50%, -100%); position: relative;">
              <div style="
                background: #fff;
                border: 2px solid #F4BA4D;
                padding: 6px 16px;
                border-radius: 999px;
                font-weight: 700;
                font-size: 14px;
                white-space: nowrap;
                box-shadow: 0 4px 12px rgba(0,0,0,.25);
              ">${job.title}</div>
              <div style="
                width: 0; height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 10px solid #F4BA4D;
                margin: 0 auto; margin-top: -1px;
              "></div>
            </div>
          `,
        },
      });

      naver.maps.Event.addListener(marker, "click", () => {
        setSelectedJob(job);
      });

      markersRef.current.push({ marker });
    });

    if (markersRef.current.length > 0 && aiMode) {
      const bounds = new window.naver.maps.LatLngBounds();
      markersRef.current.forEach(({ marker }) =>
        bounds.extend(marker.getPosition())
      );
      mapRef.current.fitBounds(bounds);
    }
  }, [mapReady, markerDataList, aiMode]);

  const moveToMyLocation = useCallback(() => {
    if (!mapRef.current) return;

    const placeMarker = (lat, lng) => {
      const pos = new window.naver.maps.LatLng(lat, lng);
      mapRef.current.setCenter(pos);
      mapRef.current.setZoom(15);
      if (window.__myPosMarker) window.__myPosMarker.setMap(null);
      window.__myPosMarker = new window.naver.maps.Marker({
        position: pos,
        map: mapRef.current,
        icon: {
          content: `
            <div style="
              background:#F4BA4D;
              color:#000000;
              font-bold;
              padding:6px 10px;
              border-radius:20px;
              font-size:12px;
              box-shadow:0 2px 6px rgba(0,0,0,.3);
            ">
              📍 내 위치
            </div>
          `,
        },
      });
      setMyPos({ lat, lng });
    };

    if (IS_CORD_FIXED && FIXED_COORD) {
      placeMarker(FIXED_COORD.lat, FIXED_COORD.lng);
      return;
    }

    if (!navigator.geolocation) {
      alert("위치를 가져올 수 없습니다. 브라우저 권한을 확인해주세요.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        if (
          Number.isFinite(coords.latitude) &&
          Number.isFinite(coords.longitude)
        ) {
          placeMarker(coords.latitude, coords.longitude);
        } else {
          alert("위치 정보를 읽을 수 없습니다.");
        }
      },
      () => alert("위치 권한을 허용해야 합니다."),
      { enableHighAccuracy: true }
    );
  }, []);

  const stopVoiceFeedback = useCallback(() => {
    if (!isVoiceRecording) return;
    aiVoiceRecorderRef.current?.stop();
    setIsVoiceRecording(false);
  }, [isVoiceRecording]);

  useEffect(() => {
    if (mapReady) moveToMyLocation();
  }, [mapReady, moveToMyLocation]);

  useEffect(() => {
    return () => {
      if (aiVoiceRecorderRef.current?.state === "recording") {
        aiVoiceRecorderRef.current.stop();
      }
    };
  }, []);

  useEffect(() => {
    if (!aiOverlayOpen && isVoiceRecording) {
      stopVoiceFeedback();
    }
  }, [aiOverlayOpen, isVoiceRecording, stopVoiceFeedback]);

  useEffect(() => {
    if (pendingCenterOnUser && mapReady) {
      moveToMyLocation();
      setPendingCenterOnUser(false);
    }
  }, [pendingCenterOnUser, mapReady, moveToMyLocation]);

  const focusMapByAddress = (address) => {
    if (!address || !window.naver?.maps?.Service || !mapRef.current) return;
    window.naver.maps.Service.geocode({ address }, (status, response) => {
      if (status !== window.naver.maps.Service.Status.OK) return;
      const result = response.result.items?.[0];
      if (!result) return;
      const lat = parseFloat(result.point.y);
      const lng = parseFloat(result.point.x);
      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        focusMapToCoords(lat, lng);
      }
    });
  };

  const normalizeAiResult = (rec) => {
    const latSource =
      rec.lat ??
      rec.latitude ??
      rec.location_latitude ??
      rec.coords?.lat ??
      rec.position?.lat;
    const lngSource =
      rec.lng ??
      rec.longitude ??
      rec.location_longitude ??
      rec.coords?.lng ??
      rec.position?.lng;
    const lat = latSource != null ? Number(latSource) : null;
    const lng = lngSource != null ? Number(lngSource) : null;
    return {
      ...rec,
      lat,
      lng,
    };
  };

  const runAiRecommendations = async (nextIntent) => {
    if (aiLoading) return;
    const intentToUse =
      typeof nextIntent === "string" ? nextIntent : aiIntent || "";
    setAiLoading(true);
    setSelectedJob(null);
    clearAiSelection();

    try {
      const query = intentToUse
        ? `/api/v1/jobs/recommend?limit=3&intent=${encodeURIComponent(
            intentToUse
          )}`
        : "/api/v1/jobs/recommend?limit=3";
      const data = await apiFetch(query);
      const recommendations = Array.isArray(data) ? data : [];

      if (!recommendations.length) {
        throw new Error("추천 결과가 없습니다.");
      }

      const normalized = recommendations.map(normalizeAiResult);
      setAiResults(normalized);
      try {
        window.localStorage.setItem(
          "last_ai_recommendations",
          JSON.stringify(normalized)
        );
        setLastAiResults(normalized);
      } catch (e) {
        console.warn("failed to persist AI recommendations", e);
      }
      setAiCoords(
        normalized.map((rec) => ({
          lat: rec.lat ?? null,
          lng: rec.lng ?? null,
        }))
      );
      setAiMode(true);
      setAiOverlayOpen(true);
      setAiIntent(intentToUse);
      setJobErr("");
    } catch (e) {
      console.error(e);
      setAiMode(false);
      setAiResults([]);
      clearAiSelection();
      setAiOverlayOpen(false);
      setAiIntent("");
      setJobErr(
        parseApiError(e, "AI 추천을 불러오는 중 문제가 발생했어요.")
      );
    } finally {
      setAiLoading(false);
    }
  };

  const handleAiButtonClick = async () => {
    if (aiLoading) return;

    if (aiMode) {
      setAiMode(false);
      setSelectedJob(null);
      setAiResults([]);
      clearAiSelection();
      setAiOverlayOpen(false);
      setAiIntent("");
      setPendingCenterOnUser(true);
      return;
    }

    await runAiRecommendations("");
  };

  const handleLoadLastRecommendations = () => {
    if (!lastAiResults || lastAiResults.length === 0) {
      alert("최근 추천 기록이 없습니다.");
      return;
    }
    const normalized = lastAiResults.map(normalizeAiResult);
    setAiResults(normalized);
    setAiCoords(
      normalized.map((rec) => ({
        lat: rec.lat ?? null,
        lng: rec.lng ?? null,
      }))
    );
    setAiMode(true);
    setAiOverlayOpen(true);
  };

  const handleVoiceFeedbackClick = () => {
    if (aiFeedbackLoading) return;
    if (isVoiceRecording) {
      stopVoiceFeedback();
    } else {
      startVoiceFeedback();
    }
  };

  const handleSubmitTextFeedback = async () => {
    if (!textFeedback.trim()) {
      setAiFeedbackError("추가 조건을 입력해주세요.");
      return;
    }
    setAiFeedbackLoading(true);
    setAiFeedbackError("");
    try {
      await runAiRecommendations(textFeedback.trim());
      setTextFeedback("");
      setShowTextFeedback(false);
    } catch (error) {
      setAiFeedbackError(parseApiError(error, "재추천에 실패했습니다."));
    } finally {
      setAiFeedbackLoading(false);
    }
  };

  const handleCloseCard = () => setSelectedJob(null);

  const handleApply = () => {
    if (selectedJob) {
      navigate(`/jobs/${selectedJob.id}`);
    }
  };

  const coerceUuidString = (value) => {
    if (value == null) return null;
    const str = typeof value === "string" ? value.trim() : String(value);
    if (!str) return null;
    const simple = /^[0-9a-fA-F]{32}$/;
    const hyphen =
      /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
    if (simple.test(str) || hyphen.test(str)) return str;
    return null;
  };

  const matchLocalJobId = (job) => {
    if (!job || !jobs?.length) return null;
    const targetTitle = (job.title || "").trim().toLowerCase();
    if (!targetTitle) return null;
    let candidates = jobs.filter(
      (j) => (j.title || "").trim().toLowerCase() === targetTitle
    );
    if (candidates.length > 1) {
      const targetLocation = (
        job.place ||
        job.location ||
        job.address ||
        job.region ||
        ""
      )
        .trim()
        .toLowerCase();
      if (targetLocation) {
        candidates = candidates.filter((j) =>
          (
            j.place ||
            j.location ||
            j.address ||
            j.region ||
            ""
          )
            .trim()
            .toLowerCase()
            .includes(targetLocation)
        );
      }
    }
    return candidates[0]?.id || null;
  };

  const getJobIdFromResult = (job) => {
    if (!job) return null;
    const candidates = [
      job.job_id,
      job.jobId,
      job.job_uuid,
      job.id,
      job.raw?.job_id,
      job.raw?.jobId,
      job.raw?.job_uuid,
      job.raw?.id,
      selectedAiDetail?.id,
    ];
    for (const value of candidates) {
      const coerced = coerceUuidString(value);
      if (coerced) return coerced;
    }
    const fallback = matchLocalJobId(job);
    return coerceUuidString(fallback);
  };

  const openAiApplyModal = (job) => {
    const targetId = getJobIdFromResult(job);
    if (!targetId) {
      alert("지원할 수 없는 공고입니다. 다른 공고를 선택해주세요.");
      return;
    }
    setAiApplyTarget({ ...job, job_id: targetId });
    setAiApplyNote("잘 부탁드립니다.");
    setAiApplyError("");
  };

  const closeAiApplyModal = () => {
    if (aiApplySubmitting) return;
    setAiApplyTarget(null);
    setAiApplyError("");
  };

  const submitAiApply = async () => {
    const jobIdRaw = getJobIdFromResult(aiApplyTarget);
    if (!jobIdRaw) {
      setAiApplyError("지원할 공고 정보를 찾을 수 없어요.");
      return;
    }
    const payloadJobId =
      typeof jobIdRaw === "string" ? jobIdRaw : String(jobIdRaw);
    setAiApplySubmitting(true);
    setAiApplyError("");
    try {
      await ApplicationsAPI.apply({
        job_id: payloadJobId,
        note: aiApplyNote,
      });
      setAiApplyTarget(null);
      alert("지원이 완료되었어요.");
    } catch (error) {
      setAiApplyError(
        parseApiError(error, "지원에 실패했습니다. 다시 시도해주세요.")
      );
    } finally {
      setAiApplySubmitting(false);
    }
  };

  const clearAiHighlight = () => {
    if (aiHighlightRef.current) {
      aiHighlightRef.current.setMap(null);
      aiHighlightRef.current = null;
    }
  };

  const clearAiSelection = () => {
    setSelectedAiResult(null);
    clearAiHighlight();
  };

  const processVoiceFeedbackBlob = async (blob) => {
    if (!blob) return;
    setAiFeedbackLoading(true);
    setAiFeedbackError("");
    try {
      const timestamp = Date.now();
      const file = new File([blob], `ai_feedback_${timestamp}.webm`, {
        type: "audio/webm",
      });
      const uploadRes = await MediaAPI.uploadAudio(file);
      const uploadId = uploadRes?.upload_ids?.[0];
      if (!uploadId) throw new Error("음성 업로드에 실패했습니다.");
      const stt = await AIAPI.parseAsr({ upload_ids: [uploadId] });
      const text = (stt?.raw_text || "").trim();
      if (!text) {
        throw new Error("음성에서 내용을 인식하지 못했습니다.");
      }
      await runAiRecommendations(text);
    } catch (error) {
      setAiFeedbackError(
        parseApiError(error, "음성을 이해하지 못했어요. 다시 시도해주세요.")
      );
    } finally {
      setAiFeedbackLoading(false);
    }
  };

  const startVoiceFeedback = async () => {
    if (isVoiceRecording) return;
    setAiFeedbackError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      aiVoiceChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          aiVoiceChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        const recorded = new Blob(aiVoiceChunksRef.current, {
          type: "audio/webm",
        });
        processVoiceFeedbackBlob(recorded);
        stream.getTracks().forEach((track) => track.stop());
      };
      aiVoiceRecorderRef.current = recorder;
      recorder.start();
      setIsVoiceRecording(true);
    } catch (error) {
      setAiFeedbackError("마이크 권한이 필요합니다.");
      setIsVoiceRecording(false);
    }
  };

  const handleSelectAiResult = async (job, idx) => {
    const jobId = getJobIdFromResult(job);
    if (!jobId) {
      console.warn("[AI] 추천 항목에 유효한 job_id가 없습니다.", job);
    }
    setSelectedAiResult({ ...job, job_id: jobId || null });
    setSelectedAiDetail(null);
    setAiOverlayOpen(false);
    setAiMode(true);
    setAiDetailLoading(Boolean(jobId));

    let { lat: latCandidate, lng: lngCandidate } = aiCoords[idx] || {
      lat: null,
      lng: null,
    };
    if (latCandidate == null || lngCandidate == null) {
      latCandidate =
        job.lat ??
        job.latitude ??
        job.location_latitude ??
        job.raw?.lat ??
        job.raw?.latitude;
      lngCandidate =
        job.lng ??
        job.longitude ??
        job.location_longitude ??
        job.raw?.lng ??
        job.raw?.longitude;
    }
    let detail = null;
    if (jobId) {
      try {
        detail = await JobsAPI.detail(jobId);
        latCandidate = detail.lat ?? latCandidate;
        lngCandidate = detail.lng ?? lngCandidate;
      } catch (err) {
        console.warn("[AI] 상세 정보를 불러오지 못했습니다.", err);
      }
    }
    setSelectedAiDetail(detail);
    setAiDetailLoading(false);

    const lat = latCandidate != null ? Number(latCandidate) : Number.NaN;
    const lng = lngCandidate != null ? Number(lngCandidate) : Number.NaN;
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      focusMapToCoords(lat, lng);
    } else {
      const fallbackAddress =
        job.place ||
        job.location ||
        job.address ||
        job.region ||
        job.raw?.place ||
        job.raw?.location ||
        job.raw?.address;
      if (fallbackAddress) {
        focusMapByAddress(fallbackAddress);
      }
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <TopBar
        showBack={false}
        showNotification
        nickname={me?.nickname}
        statusText={
          aiLoading
            ? "AI 추천중…"
            : aiMode
            ? "맞춤 소일자리 추천"
            : "현재 위치 기준 소일거리"
        }
      />

      {(() => {
        const messages = [
          err,
          jobErr,
          mapError && `지도 로드 오류: ${mapError}`,
        ].filter(Boolean);
        if (!messages.length) return null;
        return (
          <div className="mx-6 mt-[90px] p-4 rounded-xl bg-red-50 text-red-600 border border-red-200">
            {messages.map((msg, idx) => (
              <p key={idx}>{msg}</p>
            ))}
          </div>
        );
      })()}

      <main className="flex-1 flex flex-col pt-[80px] pb-[120px] relative">
        <div className="absolute inset-0">
          <div ref={mapBoxRef} className="w-full h-full">
            {(!loaded || !mapReady) && (
              <div className="w-full h-full flex items-center justify-center bg-gray-100">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-customorange mx-auto mb-4"></div>
                  <p className="text-gray-600">
                    {loaded ? "지도를 준비 중..." : "지도를 불러오는 중..."}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* AI 추천 버튼 */}
          <button
            onClick={handleAiButtonClick}
            disabled={aiLoading}
            className={`
             absolute top-24 left-1/2 -translate-x-1/2 z-50
              px-5 py-2 rounded-full backdrop-blur bg-orange-500/10 border-orange-500
              font-semibold shadow-md transition text-xl
              ${
                aiMode
                  ? "text-white bg-customorange border-orange"
                  : "text-customorange border-orange"
              }
              ${
                aiLoading
                  ? "opacity-60 cursor-not-allowed"
                  : "hover:bg-customorange hover:text-white"
              }
            `}
          >
            {aiLoading ? "AI 추천중…" : aiMode ? "근처 보기" : "⭐️AI 추천⭐️"}
          </button>

          {/* 최근 추천 목록 버튼 */}
          <button
            onClick={handleLoadLastRecommendations}
            className="absolute top-36 left-1/2 -translate-x-1/2 z-40 px-4 py-2 rounded-full bg-white/90 border text-sm font-semibold text-gray-700 shadow"
          >
            ⏱ 최근 추천 목록
          </button>

          {/* ✅ 예전 스타일의 내 위치 버튼 복원 */}
          <button
            onClick={moveToMyLocation}
            className="absolute bottom-14 right-4 z-50"
          >
            <div className="flex flex-col items-center gap-1">
              {/* 동그란 아이콘 영역 */}
              <div
                className="
                  w-12 h-12 
                  rounded-full 
                  bg-white/95 backdrop-blur
                  border-2 border-orange-500
                  shadow-[0_4px_12px_rgba(0,0,0,0.25)]
                  grid place-items-center
                "
              >
                {/* 채워진 오렌지 지도핀 아이콘 */}
                <svg
                  viewBox="0 0 24 24"
                  className="w-7 h-7 text-orange-500"
                  fill="currentColor"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path
                    d="
                      M12 2
                      C8 2 5 5 5 9
                      C5 14 12 22 12 22
                      C12 22 19 14 19 9
                      C19 5 16 2 12 2
                    "
                  />
                  <circle cx="12" cy="9" r="3" fill="white" />
                </svg>
              </div>

              {/* 라벨 */}
              <span
                className="
                  px-3 py-[2px]
                  text-[12px] font-semibold
                  rounded-full
                  bg-white/90 backdrop-blur
                  text-gray-900
                  border-2 border-orange-500
                  shadow-sm
                "
              >
                내 위치
              </span>
            </div>
          </button>
        </div>

        {aiLoading && (
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm z-[60] flex flex-col items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-white border-t-transparent mb-4"></div>
            <p className="text-white font-semibold text-lg">AI 추천중···</p>
            <p className="text-white/80 text-sm mt-2">
              맞춤형 소일거리를 찾는 중이에요
            </p>
          </div>
        )}

        {aiMode && aiOverlayOpen && !aiLoading && aiResults.length > 0 && (
          <div className="absolute inset-x-4 top-28 z-50 pointer-events-auto">
            <div className="bg-white/90 rounded-3xl shadow-2xl p-4 max-w-2xl mx-auto">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-xs text-gray-500">AI 추천 결과</p>
                  <h3 className="text-lg font-bold">프로필 기반 맞춤 소일거리</h3>
                </div>
                <button
                  onClick={() => setAiOverlayOpen(false)}
                  className="text-gray-500 hover:text-gray-800"
                  aria-label="AI 추천 닫기"
                >
                  ✕
                </button>
              </div>
              <div className="grid gap-3">
                {aiResults.map((rec, idx) => (
                  <button
                    key={`${rec.job_id || rec.title || idx}-${idx}`}
                    onClick={() => handleSelectAiResult(rec, idx)}
                    className={`text-left ${
                      selectedAiResult === rec
                        ? "ring-2 ring-orange-400 rounded-2xl"
                        : ""
                    }`}
                  >
                    <AIResultCard job={rec} />
                  </button>
                ))}
              </div>
              <div className="mt-4 bg-orange-50 rounded-2xl p-4 border border-orange-200">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xl font-bold text-orange-700">
                    🔄 재추천 요청
                  </p>
                  {aiFeedbackLoading && (
                    <span className="text-sm text-orange-600 animate-pulse">
                      처리중...
                    </span>
                  )}
                </div>
                <p className="text-sm text-orange-700 mb-3">
                  더 원하는 조건이 있다면 목소리나 글자로 알려주세요.
                </p>
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={handleVoiceFeedbackClick}
                    className={`flex items-center gap-2 px-5 py-3 rounded-2xl font-bold text-lg shadow ${
                      isVoiceRecording
                        ? "bg-red-500 text-white"
                        : "bg-white text-orange-600 border border-orange-300"
                    } ${aiFeedbackLoading ? "opacity-60 cursor-not-allowed" : ""}`}
                    disabled={aiFeedbackLoading}
                  >
                    <Mic className="w-5 h-5" />
                    {isVoiceRecording ? "녹음 중지" : "마이크"}
                  </button>
                  <button
                    onClick={() => {
                      setShowTextFeedback((prev) => !prev);
                      setAiFeedbackError("");
                    }}
                    className={`flex items-center gap-2 px-5 py-3 rounded-2xl font-bold text-lg shadow ${
                      showTextFeedback
                        ? "bg-orange-500 text-white"
                        : "bg-white text-orange-600 border border-orange-300"
                    }`}
                  >
                    <PenLine className="w-5 h-5" />
                    글자로 입력
                  </button>
                </div>
                {showTextFeedback && (
                  <div className="mt-4 flex flex-col gap-2">
                    <textarea
                      value={textFeedback}
                      onChange={(e) => setTextFeedback(e.target.value)}
                      rows={2}
                      className="w-full rounded-2xl border-2 border-orange-200 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-orange-400"
                      placeholder="예: 강동구 오후 시간대 청소 일을 추천해주세요."
                    />
                    <button
                      onClick={handleSubmitTextFeedback}
                      disabled={aiFeedbackLoading}
                      className="self-end px-6 py-3 bg-orange-500 text-white rounded-2xl font-bold shadow hover:bg-orange-600 disabled:opacity-60"
                    >
                      재추천 받기
                    </button>
                  </div>
                )}
                {aiFeedbackError && (
                  <p className="mt-3 text-sm text-red-600">{aiFeedbackError}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {selectedAiResult && (
          <div className="absolute top-28 right-4 max-w-sm bg-white rounded-2xl shadow-2xl z-40 p-6 border border-orange-100">
            <div className="flex justify-between items-start mb-3">
              <div>
                <p className="text-xs text-orange-500 font-semibold">AI 추천</p>
                <h3 className="text-xl font-bold">
                  {selectedAiResult.title || "추천 공고"}
                </h3>
              </div>
              <button
                onClick={clearAiSelection}
                className="text-gray-400 hover:text-gray-600"
                aria-label="추천 상세 닫기"
              >
                ✕
              </button>
            </div>
            <div className="flex justify-between mb-4">
              <button
                onClick={() => {
                  clearAiSelection();
                  setAiOverlayOpen(true);
                }}
                className="text-sm text-gray-500 hover:text-gray-800 underline"
              >
                ← 목록으로
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-1">
              📍{" "}
              {selectedAiResult.place ||
                selectedAiResult.location ||
                selectedAiResult.address ||
                "지역 정보 없음"}
            </p>
            <p className="text-sm text-gray-600 mb-3">
              💰{" "}
              {selectedAiResult.pay_text ||
                (selectedAiResult.hourly_wage != null
                  ? `시급 ${toCurrency(selectedAiResult.hourly_wage)}`
                  : "협의")}
            </p>
            {aiDetailLoading && (
              <p className="text-xs text-gray-400 mb-2">
                상세 정보를 불러오는 중...
              </p>
            )}
            {(selectedAiResult.description ||
              selectedAiDetail?.description) && (
              <p className="text-sm text-gray-700 whitespace-pre-line mb-3">
                {selectedAiResult.description || selectedAiDetail?.description}
              </p>
            )}
            <p className="text-sm text-emerald-700 font-semibold mb-4">
              추천 이유:{" "}
              {selectedAiResult.recommendation_reason ||
                "AI가 프로필과 잘 맞다고 판단했어요."}
            </p>
            <button
              onClick={() => openAiApplyModal(selectedAiResult)}
              disabled={!getJobIdFromResult(selectedAiResult)}
              className={`w-full text-center rounded-xl py-3 font-semibold ${
                getJobIdFromResult(selectedAiResult)
                  ? "bg-orange-500 text-white hover:bg-orange-600"
                  : "bg-gray-200 text-gray-500 cursor-not-allowed"
              }`}
            >
              {getJobIdFromResult(selectedAiResult)
                ? "지원하기"
                : "지원 준비 중"}
            </button>
          </div>
        )}

        {selectedJob && (
          <div className="absolute inset-0 z-[55] flex items-center justify-center">
            {/* 반투명 배경 (밖 클릭 시 닫기) */}
            <div
              className="absolute inset-0 bg-black/30"
              onClick={handleCloseCard}
            />

            {/* 가운데 카드 */}
            <div className="relative bg-white rounded-2xl shadow-2xl max-w-sm w-[85%] p-6">
              {/* 헤더 */}
              <div className="flex justify-between items-start mb-4">
                <div>
                  <p className="text-xs text-gray-400 mb-1">
                    추천 일자리 #{selectedJob.id}
                  </p>
                  <h2 className="text-xl font-bold">{selectedJob.title}</h2>
                </div>
                <button
                  onClick={handleCloseCard}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              {/* 내용 */}
              <div className="space-y-3 mb-5 text-sm text-gray-700">
                <p className="flex items-center">
                  <span className="mr-2 text-lg">📍</span>
                  <span className="font-medium">{selectedJob.location}</span>
                </p>
                <p className="flex items-center">
                  <span className="mr-2 text-lg">⏰</span>
                  <span className="font-medium">{selectedJob.shift}</span>
                </p>
                <p className="flex items-center">
                  <span className="mr-2 text-lg">💰</span>
                  <span className="text-customorange font-bold text-base">
                    {selectedJob.wage}
                  </span>
                </p>
              </div>

              {/* 버튼 */}
              <button
                onClick={handleApply}
                className="w-full bg-customorange text-white py-3 rounded-xl font-semibold hover:opacity-90 transition"
              >
                지원하기
              </button>
            </div>
          </div>
        )}
      </main>

      {aiApplyTarget && (
        <div className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={closeAiApplyModal} />
          <div className="relative w-full max-w-md bg-white rounded-t-3xl sm:rounded-2xl shadow-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-xs text-orange-500 font-semibold">AI 추천 공고</p>
                <h3 className="text-xl font-bold text-gray-900">
                  {aiApplyTarget.title || "추천 공고"}
                </h3>
              </div>
              <button
                type="button"
                onClick={closeAiApplyModal}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-1">
              📍{" "}
              {aiApplyTarget.place ||
                aiApplyTarget.location ||
                aiApplyTarget.address ||
                "지역 정보 없음"}
            </p>
            <p className="text-sm text-gray-600 mb-4">
              💰{" "}
              {aiApplyTarget.pay_text ||
                (aiApplyTarget.hourly_wage != null
                  ? `시급 ${toCurrency(aiApplyTarget.hourly_wage)}`
                  : "협의")}
            </p>
            <label className="block text-sm text-gray-700 mb-2">
              한 줄 메시지
            </label>
            <textarea
              className="w-full rounded-2xl border border-gray-200 p-3 text-sm text-gray-800"
              rows={4}
              value={aiApplyNote}
              onChange={(e) => setAiApplyNote(e.target.value)}
              maxLength={200}
            />
            {aiApplyError && (
              <p className="text-sm text-rose-600 mt-3">{aiApplyError}</p>
            )}
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                onClick={closeAiApplyModal}
                disabled={aiApplySubmitting}
                className="flex-1 h-12 rounded-xl border border-gray-200 text-gray-600"
              >
                취소
              </button>
              <button
                type="button"
                onClick={submitAiApply}
                disabled={aiApplySubmitting}
                className="flex-1 h-12 rounded-xl bg-orange-500 text-white font-semibold disabled:opacity-60"
              >
                {aiApplySubmitting ? "지원 중..." : "지원하기"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="fixed bottom-0 left-0 right-0 z-40">
        <BottomNav active="home" />
      </div>

      <style jsx>{`
        @keyframes slide-up {
          from {
            transform: translateY(100%);
          }
          to {
            transform: translateY(0);
          }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
