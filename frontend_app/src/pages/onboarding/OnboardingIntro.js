import React from "react";
import { useNavigate } from "react-router-dom";

export default function OnboardingIntro() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b">
        <div className="max-w-md mx-auto px-6 py-4 flex items-center justify-between">
          <div className="w-10" />
          <h1 className="text-lg font-bold">회원가입 완료</h1>
          <div className="w-10" />
        </div>
      </header>

      <main className="max-w-md mx-auto px-6 py-12">
        <div className="text-center mt-10 mb-12">
          {/* 체크 아이콘 원형 배지 */}
          <div className="w-24 h-24 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-8 shadow-sm">
            <svg className="w-12 h-12 text-white" viewBox="0 0 24 24" fill="none">
              <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>

          <h2 className="text-3xl font-bold mb-4 leading-snug">
            회원가입이 완료되었어요!
          </h2>
          <p className="text-gray-600 text-lg">
            이제 프로필 설정을 하러 가볼까요?
          </p>
        </div>

        {/* 온보딩 진행바 (0/6) */}
        <div className="mb-10">
          <div className="flex gap-1">
            {[1,2,3,4,5,6].map((i)=>(
              <div key={i} className={`flex-1 h-1.5 rounded ${i <= 0 ? "bg-customorange" : "bg-gray-200"}`} />
            ))}
          </div>
          <p className="text-sm text-gray-500 mt-2 text-center">0/6 단계</p>
        </div>

        {/* 액션 버튼 */}
        <button
          type="button"
          onClick={() => navigate("/onboarding/nickname")}
          className="w-full bg-orange-500 text-white font-bold text-xl py-5 rounded-xl
                     hover:brightness-95 focus:outline-none active:!text-white"
        >
          프로필 설정 시작하기
        </button>

        <button
          type="button"
          onClick={() => navigate("/main")}
          className="w-full mt-3 bg-gray-100 text-gray-700 font-bold text-xl py-5 rounded-xl
                     hover:bg-gray-200 focus:outline-none"
        >
          나중에 할래요
        </button>

        {/* 안내 문구 */}
        <p className="mt-6 text-center text-sm text-gray-500">
          프로필은 언제든지 마이페이지에서 변경할 수 있어요.
        </p>
      </main>
    </div>
  );
}