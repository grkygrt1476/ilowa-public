import React from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";


export default function MainScreen() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-50 to-white flex flex-col">
      <main className="max-w-7xl mx-auto px-4 py-12 flex flex-col items-center justify-center flex-1">
        <div className="text-center mb-12">
          <p className="text-lg font-bold text-orange-700 mt-12">
            집에만 있으면 심심하니까,
          </p>
          <div className="flex justify-center">
            <img
              src="/logo.png"
              alt="일로와 로고"
              className="w-60 h-60 object-contain mt-4"
            />
          </div>
        </div>

        {/* 버튼 영역 */}
        <div className="w-full max-w-sm flex flex-col items-center gap-5 mt-4">
          {/* 회원가입 버튼 */}
          <button
            onClick={() => navigate("/register")}
            className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold text-lg py-4 rounded-2xl shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
          >
            회원가입
          </button>

          {/* 로그인 버튼 */}
          <button
            onClick={() => navigate("/login")}
            className="w-full bg-white border border-orange-500 text-black-600 hover:bg-orange-50 font-bold text-lg py-4 rounded-2xl shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
          >
            로그인
          </button>
          {/* 관리자 계정 링크 */}
          <button
            onClick={() => navigate("/adminlogin")}
            className="mt-1 text-sm text-gray-600 underline underline-offset-2 hover:text-gray-800"
          >
            관리자 계정
          </button>
        </div>
      </main>
    </div>
  );
}