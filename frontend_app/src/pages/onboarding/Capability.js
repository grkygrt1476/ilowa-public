import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";

const BASE_URL = "http://127.0.0.1:8000";
const getToken =
  () => (typeof window !== "undefined" ? localStorage.getItem("access_token") : null) || "";

export default function Capability() {
  const nav = useNavigate();
  const [selectedLevel, setSelectedLevel] = useState("");
  const [saving, setSaving] = useState(false);

  const levels = [
    { id: "high", label: "힘든 일도 괜찮아요", desc: "계단 오르기, 무거운 물건 들기 가능" },
    { id: "medium", label: "적당한 활동이 좋아요", desc: "걷기, 서서 일하기 가능" },
    { id: "low", label: "가벼운 일이 좋아요", desc: "앉아서 할 수 있는 일 선호" },
  ];

  /** ✅ 저장 API */
  const save = async () => {
    const token = getToken();
    if (!token) return alert("로그인 토큰이 없습니다.");
    if (!selectedLevel) return alert("신체 능력 수준을 선택해주세요.");
    try {
      setSaving(true);
      const res = await fetch(`${BASE_URL}/api/v1/profile/prefs/capability`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ physical_level: selectedLevel }),
      });
      if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
    } catch (e) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };

  /** ✅ 이동 함수 */
  const handleNext = () => nav("/onboarding/summary", { replace: true });
  const handleSkip = () => nav("/onboarding/summary", { replace: true });
  const handleBack = () => nav(-1);

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* 상단바 */}
      <header className="fixed top-0 left-0 right-0 bg-white px-6 py-7 flex items-center justify-between border-b z-50">
        <button onClick={handleBack} className="p-2">
          <ChevronLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold">신체 능력</h1>
        <button
          onClick={handleSkip}
          className="text-black-500 font-medium text-base"
        >
          건너뛰기
        </button>
      </header>

      {/* 프로그레스바 */}
      <div className="mt-[92px]">
      <div className="px-6 py-4">
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5, 6].map((step) => (
            <div
              key={step}
              className={`flex-1 h-2 rounded ${
                step <= 5 ? "bg-orange-500" : "bg-gray-200"
              }`}
            />
          ))}
        </div>
        <p className="text-sm text-gray-500 mt-2 text-center">5/6 단계</p>
      </div>
      </div>

      {/* 메인 콘텐츠 */}
      <main className="flex-1 px-6 py-8 pb-[120px]">
        <h2 className="text-3xl font-bold mb-3">
          어떤 강도의 일이<br />편하신가요?
        </h2>
        <p className="text-gray-600 text-lg mb-8">
          신체적 작업 수준을 알려주세요
        </p>

        <div className="space-y-4 mb-8">
            {levels.map((level) => {
                const isActive = selectedLevel === level.id;
                return (
                <button
                    key={level.id}
                    onClick={() => setSelectedLevel(level.id)}
                    type="button"
                    className={`w-full p-5 rounded-2xl border-2 text-left transition-colors duration-150
                    ${isActive
                        ? "border-orange-500 bg-orange-500/10"
                        : "border-gray-300 bg-white hover:border-orange-400 hover:bg-orange-500/50"}`}
                >
                    <div className="flex items-start gap-4">
                    {/* 라디오 아이콘 */}
                    <div
                        className={`mt-1 w-7 h-7 rounded-full border-2 flex items-center justify-center
                        ${isActive ? "border-orange-500/10 bg-white" : "border-gray-300 bg-white"}`}
                    >
                        {isActive && <div className="w-3.5 h-3.5 bg-orange-500 rounded-full" />}
                    </div>

                    {/* 텍스트 */}
                    <div className="flex-1">
                        <p className={`mb-1 text-xl font-extrabold ${isActive ? "text-gray-900" : "text-gray-900"}`}>
                        {level.label}
                        </p>
                        <p className="text-base text-gray-500">{level.desc}</p>
                    </div>
                    </div>
                </button>
                );
            })}
            </div>

        {/* 안내 문구 */}
        <div className="border-orange-500/10 bg-orange-500/10 p-4 rounded-xl">
          <p className="text-sm text-gray-700">
            💡 건강 상태에 맞는 업무를 추천해드릴게요.
          </p>
        </div>
      </main>

      {/* 하단바 */}
      <footer className="fixed bottom-0 left-0 right-0 z-40 px-6 py-5 border-t bg-white">
        <button
          type="button"
          onClick={async () => {
            await save();
            handleNext();
          }}
          disabled={saving || !selectedLevel}
          className="w-full bg-orange-500 text-white font-bold text-xl py-5 rounded-xl
                    disabled:bg-gray-300 disabled:cursor-not-allowed
                    "
        >
          {saving ? "저장 중..." : "다음"}
        </button>
      </footer>
    </div>
  );
}
