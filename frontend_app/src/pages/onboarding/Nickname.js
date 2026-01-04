import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";

const BASE_URL = "http://127.0.0.1:8000";
const getToken = () => (typeof window !== "undefined" ? localStorage.getItem("access_token") : null) || "";

export default function Nickname() {
  const nav = useNavigate();
  const [nickname, setNickname] = useState("");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (nickname.trim().length < 2) return;
    const token = getToken();
    if (!token) return alert("로그인 토큰이 없습니다.");
    try {
      setSaving(true);

      const r = await fetch(`${BASE_URL}/api/v1/profile/account`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ nickname }),
      });
      if (!r.ok) throw new Error((await r.text()) || `HTTP ${r.status}`);
      nav("/onboarding/location", { replace: true });
    } catch (e) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
    nav("/onboarding/location", { replace: true });
  };

    const handleBack = () => {
    nav("/register", { state: { step: 4 } }); // 회원가입의 PIN 단계로 이동
    };

  const handleSkip = () => {
    // 건너뛰기 처리 - 다음 단계로 이동하거나 홈으로 이동
    nav("/onboarding/location", { replace: true });
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* 헤더 */}
      <header className="px-6 py-7 flex items-center justify-between border-b">
        <button onClick={handleBack} className="p-2">
          <ChevronLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold">프로필 설정</h1>
        <button 
          onClick={handleSkip}
          className="text-black-500 font-sm text-base"
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
              className={`flex-1 h-2 rounded ${
                step <= 1 ? "bg-orange-500" : "bg-gray-200"
              }`}
            />
          ))}
        </div>
        <p className="text-sm text-gray-500 mt-2 text-center">1/6 단계</p>
      </div>

      {/* 메인 컨텐츠 */}
      <main className="flex-1 max-w-md mx-auto w-full px-6 py-8">
        <h2 className="text-3xl font-bold mb-4">닉네임을<br/>입력해주세요</h2>
        <p className="text-gray-600 text-lg mb-8">
          다른 사용자에게 보여질 이름이에요
        </p>
        
        <input
          className="w-full px-6 py-5 text-xl border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          maxLength={20}
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          placeholder="2~20자"
        />
        <p className="text-sm text-gray-500 mt-2">
          {nickname.length}/20자
        </p>
      </main>

      {/* 하단 버튼 */}
      <footer className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 py-4 z-40">
        <div className="max-w-7xl mx-auto px-4">
          <button
            type="button"
            onClick={async () => {
              await save();        // ✅ 비동기 저장 완료 후
              handleSkip();        // ✅ 다음 단계로 이동
            }}
            disabled={saving || nickname.trim().length < 2}
            className="w-full bg-orange-500 text-white font-bold text-xl py-5 rounded-xl
                      disabled:bg-gray-300 disabled:cursor-not-allowed
                      hover:bg-orange-600 transition"
          >
            다음
          </button>
        </div>
      </footer>
    </div>
  );
}
