//정보 입력 요약 페이지
// src/pages/onboarding/OnboardingSummary.js
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";

const BASE_URL = "http://127.0.0.1:8000";
const getToken =
  () => (typeof window !== "undefined" ? localStorage.getItem("access_token") : null) || "";

export default function OnboardingSummary() {
  const navigate = useNavigate();
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState({
    location: "-",
    days: [],
    time_slots: [],
    experiences: [],
    physical: "-",
    nickname: "",
  });

  // 요약 데이터 불러오기 (GET /profile/summary)
  useEffect(() => {
    const fetchSummary = async () => {
      const token = getToken();
      if (!token) return;
      try {
        const r = await fetch(`${BASE_URL}/profile/summary`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json().catch(() => ({}));

        const loc =
          data?.prefs?.location?.regions?.[0] ||
          data?.region ||
          data?.prefs?.region ||
          "-";
        const days = data?.prefs?.days || data?.days || [];
        const timeSlots = data?.prefs?.time_slots || data?.time_slots || [];
        const exps = data?.experiences || data?.prefs?.experiences || [];
        const physical =
          data?.prefs?.physical_level ||
          data?.physical_level ||
          (data?.capabilities
            ? data.capabilities.can_stand_long
              ? "적당한 활동이 좋아요"
              : "가벼운 일이 좋아요"
            : "-");

        setSummary({
          location: loc,
          days,
          time_slots: timeSlots,
          experiences: exps,
          physical,
          nickname: data?.nickname || "",
        });
      } catch {
        // 실패해도 페이지는 기본값으로 표시
      }
    };
    fetchSummary();
  }, []);

  const finish = async () => {
    const token = getToken();
    if (!token) return alert("로그인 토큰이 없습니다.");
    if (!consent) return;

    try {
      setLoading(true);
      const r = await fetch(`${BASE_URL}/api/v1/profile/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      if (!r.ok) throw new Error((await r.text()) || `HTTP ${r.status}`);
      navigate("/main", { replace: true });
    } catch (e) {
      alert(e.message || "저장에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const back = () => navigate(-1);

  return (
    <div className="min-h-[100dvh] bg-white flex flex-col overflow-y-auto">
      {/* 상단바 고정 */}
      <header className="fixed top-0 left-0 right-0 bg-white px-6 py-7 flex items-center justify-between border-b z-50">
        <button onClick={back} className="p-2" type="button">
          <ChevronLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold">정보 확인</h1>
        <div className="w-10" />
      </header>

      {/* 상단바 높이만큼 오프셋 */}
      <div className="mt-[92px]">
        {/* 프로그레스바 (6/6) */}
        <div className="px-6 py-4">
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5, 6].map((s) => (
              <div
                key={s}
                className={`flex-1 h-2 rounded ${s <= 6 ? "bg-orange-500" : "bg-gray-200"}`}
              />
            ))}
          </div>
          <p className="text-sm text-gray-500 mt-2 text-center">6/6 단계</p>
        </div>

        {/* 본문: 하단 고정 푸터 높이만큼 패딩 추가 */}
        <main
          className="flex-1 px-6 py-4 pb-[120px]"
          style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 120px)" }}
        >
          <h2 className="text-3xl font-bold mb-3">
            입력하신 정보를
            <br />
            확인해주세요
          </h2>
          <p className="text-gray-600 text-lg mb-8">
            이 정보로 맞춤 일자리를 추천해드려요
          </p>

          <div className="bg-gray-50 rounded-xl p-5 mb-8 space-y-4">
            <div>
              <p className="text-sm text-gray-500 mb-1">닉네임</p>
              <p className="font-bold text-lg">{summary.nickname || "-"}</p>
            </div>
            <div className="h-px bg-gray-200" />

            <div>
              <p className="text-sm text-gray-500 mb-1">선호 지역</p>
              <p className="font-bold text-lg">{summary.location || "-"}</p>
            </div>
            <div className="h-px bg-gray-200" />

            <div>
              <p className="text-sm text-gray-500 mb-1">선호 요일</p>
              <p className="font-bold text-lg">
                {summary.days?.length ? summary.days.join(", ") : "-"}
              </p>
            </div>
            <div className="h-px bg-gray-200" />

            <div>
              <p className="text-sm text-gray-500 mb-1">선호 시간</p>
              <p className="font-bold text-lg">
                {summary.time_slots?.length ? summary.time_slots.join(", ") : "-"}
              </p>
            </div>
            <div className="h-px bg-gray-200" />

            <div>
              <p className="text-sm text-gray-500 mb-1">과거 경험</p>
              <p className="font-bold text-lg">
                {summary.experiences?.length ? summary.experiences.join(", ") : "-"}
              </p>
            </div>
            <div className="h-px bg-gray-200" />

            <div>
              <p className="text-sm text-gray-500 mb-1">신체 활동 수준</p>
              <p className="font-bold text-lg">{summary.physical || "-"}</p>
            </div>
          </div>

          {/* 동의 체크 */}
          <button
            type="button"
            onClick={() => setConsent((v) => !v)}
            className="w-full flex items-start gap-3 p-4 border-2 rounded-xl cursor-pointer
                       transition-colors border-gray-200 hover:border-orange-400 bg-orange-500/10"
          >
            <div
              className={`w-6 h-6 rounded flex items-center justify-center flex-shrink-0 mt-1 ${
                consent ? "bg-orange-500" : "bg-white border-2 border-gray-300"
              }`}
            >
              {consent && (
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24">
                  <path
                    d="M5 13l4 4L19 7"
                    stroke="currentColor"
                    strokeWidth={3}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">
              선택 데이터 수집 및 맞춤형 추천 알림 수신에 동의합니다
            </p>
          </button>
        </main>
      </div>

      {/* 하단 버튼 고정 */}
      <footer className="fixed bottom-0 left-0 right-0 border-t bg-white px-6 py-4 z-40">
        <button
          onClick={finish}
          disabled={!consent || loading}
          className="w-full bg-orange-500 text-white font-bold text-xl py-5 rounded-xl
                     disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-orange-600 transition"
        >
          {loading ? "저장 중..." : "제출"}
        </button>
      </footer>
    </div>
  );
}