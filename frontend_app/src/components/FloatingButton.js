// src/components/FloatingButton.js
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function FloatingButton() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  const handleNavigation = (path) => {
    navigate(path);
    setIsOpen(false);
  };

  return (
    <div className="fixed bottom-24 right-6 ">
      {/* 옵션 버튼들 */}
      {isOpen && (
        <div className="mb-4 space-y-3 animate-fade-in">
          {/* 음성 기반 공고 등록 */}
          <button
            onClick={() => handleNavigation("/jobs/from-voice/record")}
            className="flex items-center gap-3 bg-white text-gray-800 px-5 py-3 rounded-full shadow-lg hover:shadow-xl transition-all w-full"
          >
            <span className="text-2xl">🎤</span>
            <span className="font-semibold whitespace-nowrap">음성 기반 공고 등록</span>
          </button>

          {/* 이미지 기반 공고 등록 */}
          <button
            onClick={() => handleNavigation("/jobs/from-image/upload")}
            className="flex items-center gap-3 bg-white text-gray-800 px-5 py-3 rounded-full shadow-lg hover:shadow-xl transition-all w-full"
          >
            <span className="text-2xl">📷</span>
            <span className="font-semibold whitespace-nowrap">이미지 기반 공고 등록</span>
          </button>

          {/* 직접 공고 등록 */}
          <button
            onClick={() => handleNavigation("/jobs/newjobmanual")}
            className="flex items-center gap-3 bg-white text-gray-800 px-5 py-3 rounded-full shadow-lg hover:shadow-xl transition-all w-full"
          >
            <span className="text-2xl">✍️</span>
            <span className="font-semibold whitespace-nowrap">직접 공고 등록</span>
          </button>
        </div>
      )}

      {/* 메인 플로팅 버튼 */}
      <button
        onClick={toggleMenu}
        className={`w-16 h-16 bg-orange-300 text-white rounded-full shadow-lg hover:shadow-xl transition-all flex items-center justify-center ${
          isOpen ? "rotate-45" : ""
        }`}
        aria-label="공고 등록"
      >
        <svg
          className="w-8 h-8"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={3}
            d="M12 4v16m8-8H4"
          />
        </svg>
      </button>

      <style jsx>{`
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in {
          animation: fade-in 0.2s ease-out;
        }
        button {
          transition: transform 0.3s ease;
        }
        .rotate-45 {
          transform: rotate(45deg);
        }
      `}</style>
    </div>
  );
}