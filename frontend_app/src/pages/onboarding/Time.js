import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";

const BASE_URL = "http://127.0.0.1:8000";
const getToken =
  () =>
    (typeof window !== "undefined" ? localStorage.getItem("access_token") : null) || "";

const DAYS = ["월", "화", "수", "목", "금", "토", "일"];
const SLOTS = ["오전", "오후", "야간", "무관"]; // ✅ '무관' 추가

export default function Time() {
  const nav = useNavigate();
  const [days, setDays] = useState([]);
  const [slots, setSlots] = useState([]); // ✅ 다중 선택 허용
  const [saving, setSaving] = useState(false);

  const toggle = (list, set, v) =>
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  // ✅ 시간대 토글: '무관'은 단독 선택, 다른 시간대 선택 시 '무관' 해제
  const toggleSlot = (v) => {
    setSlots((prev) => {
      if (v === "무관") {
        // 무관을 누르면 단독 토글
        return prev.includes("무관") ? [] : ["무관"];
        }
      // 다른 시간대를 누르면 무관 제거하고 토글
      const withoutAny = prev.filter((x) => x !== "무관");
      return withoutAny.includes(v)
        ? withoutAny.filter((x) => x !== v)
        : [...withoutAny, v];
    });
  };

  const save = async () => {
    const token = getToken();
    if (!token) return alert("로그인 토큰이 없습니다.");

    try {
      setSaving(true);
      const res = await fetch(`${BASE_URL}/api/v1/profile/prefs/time`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ days, time_slots: slots }),
      });

      if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
    } catch (err) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleNext = () => nav("/onboarding/history", { replace: true });
  const handleSkip = () => nav("/onboarding/history", { replace: true });

  const canProceed = days.length > 0 && slots.length > 0;

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* 상단 바 */}
      <header className="px-6 py-7 flex items-center justify-between border-b">
        <button type="button" className="p-2" onClick={() => nav(-1)}>
          <ChevronLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold">선호 요일/시간</h1>
        <button
          type="button"
          onClick={handleSkip}
          className="text-customorange font-semibold text-base"
        >
          건너뛰기
        </button>
      </header>

      {/* 프로그레스바 */}
      <div className="px-6 py-4">
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5, 6].map((step) => (
            <div
              key={step}
              className={`flex-1 h-2 rounded ${step <= 3 ? "bg-orange-500" : "bg-gray-200"}`}
            />
          ))}
        </div>
        <p className="text-sm text-gray-500 mt-2 text-center">3/6 단계</p>
      </div>

      {/* 본문 */}
      <main className="flex-1 px-6 py-8 pb-32">
        <h2 className="text-3xl font-bold mb-3">
          언제 일하고<br />
          싶으신가요?
        </h2>
        <p className="text-gray-600 mb-4">선호 요일과 시간대를 선택해주세요</p>

        {/* 안내 */}
        <div className="mb-6 rounded-xl bg-orange-500/10 text-black-800 text-sm px-4 py-3">
          💡 요일과 시간대는 <b>여러 개 중복 선택</b>할 수 있어요.<br />
        </div>

        {/* 요일 선택 */}
        <h3 className="font-bold mb-2 text-lg">요일</h3>
        <div className="grid grid-cols-7 gap-2 mb-6">
          {DAYS.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => toggle(days, setDays, d)}
              className={`py-2 rounded-lg border-2 font-medium transition-colors
                ${
                  days.includes(d)
                    ? "border-orange-500 bg-orange-500/10 text-white"
                    : "border-gray-300 bg-white text-gray-800 hover:border-gray-400"
                }`}
            >
              {d}
            </button>
          ))}
        </div>

        {/* 시간대 선택 (무관 포함/다중 선택) */}
        <h3 className="font-bold mb-2 text-lg">시간대</h3>
        <div className="grid grid-cols-4 gap-3">
          {SLOTS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => toggleSlot(s)}  // ✅ 변경
              className={`py-3 rounded-lg border-2 font-medium transition-colors
                ${
                  slots.includes(s)
                    ? "border-orange-500 bg-orange-500/10 text-white"
                    : "border-gray-300 bg-white text-gray-800 hover:border-gray-400"
                }`}
            >
              {s}
            </button>
          ))}
        </div>
      </main>

      {/* 하단 버튼 (공통 컨테이너 폭) */}
      <footer className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 py-4 z-40">
        <div className="max-w-7xl mx-auto px-4">
          <button
            type="button"
            onClick={async () => {
              await save();
              handleNext();
            }}
            disabled={saving || !canProceed}
            className={`w-full font-bold text-xl py-5 rounded-xl transition
              ${
                !canProceed
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