// src/components/BottomNav.js
import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);

  const isActive = (path) => location.pathname === path;
  const toggleMenu = () => setIsOpen((prev) => !prev);
  const handleNavigation = (path) => {
    navigate(path);
    setIsOpen(false);
  };

  /* --------------------  각 탭 Item  -------------------- */
  const Item = ({ active, onClick, icon, label }) => (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className="group flex flex-col items-center gap-1.5 flex-1 cursor-pointer"
    >
      <div
        className={[
          "grid place-items-center rounded-full border-2 transition-all duration-200",
          "w-11 h-11",
          active
            ? "bg-orange-500 text-white border-orange-500 shadow-lg animate-pop"
            : "bg-white text-gray-700 border-orange-200",
        ].join(" ")}
      >
        <div className="w-6 h-6">{icon}</div>
      </div>

      {/* 👉 글씨 항상 검정 */}
      <span className="text-[15px] tracking-tight font-semibold text-black">
        {label}
      </span>
    </button>
  );

  return (
    <>
      <style>{`
        @keyframes popUp {
          0%   { transform: translateY(4px) scale(0.94); }
          55%  { transform: translateY(-4px) scale(1.06); }
          100% { transform: translateY(0) scale(1); }
        }
        .animate-pop { animation: popUp 220ms cubic-bezier(.2,.9,.25,1) both; }

        @keyframes fade-in {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fade-in 0.2s ease-out;
        }
        .rotate-45 {
          transform: rotate(45deg);
        }
      `}</style>

      {/* 상단 요소들이 클릭을 막지 않도록 pointer-events 조절 */}
      <nav className="fixed inset-x-0 bottom-0 z-[9999] pb-[calc(env(safe-area-inset-bottom,0)+6px)] pointer-events-none">
        <div className="pointer-events-auto mx-auto w-full max-w-md flex justify-center">
          <div className="relative w-[393px] h-[165px] flex items-end justify-center">
            {/* --------------------  + 버튼 눌렀을 때 보여줄 메뉴  -------------------- */}
            {isOpen && (
              <div className="absolute right-[30px] bottom-[120px] mb-3 space-y-3 animate-fade-in z-30">
                <button
                  onClick={() => handleNavigation("/jobs/from-voice/record")}
                  className="flex items-center gap-3 bg-white text-gray-800 px-5 py-3 rounded-full shadow-lg hover:shadow-xl transition-all w-full cursor-pointer"
                >
                  <span className="text-2xl">🎤</span>
                  <span className="font-semibold whitespace-nowrap">
                    음성 기반 공고 등록
                  </span>
                </button>

                <button
                  onClick={() => handleNavigation("/jobs/from-image/upload")}
                  className="flex items-center gap-3 bg-white text-gray-800 px-5 py-3 rounded-full shadow-lg hover:shadow-xl transition-all w-full cursor-pointer"
                >
                  <span className="text-2xl">📷</span>
                  <span className="font-semibold whitespace-nowrap">
                    이미지 기반 공고 등록
                  </span>
                </button>

                <button
                  onClick={() => handleNavigation("/jobs/newjobmanual")}
                  className="flex items-center gap-3 bg-white text-gray-800 px-5 py-3 rounded-full shadow-lg hover:shadow-xl transition-all w-full cursor-pointer"
                >
                  <span className="text-2xl">✍️</span>
                  <span className="font-semibold whitespace-nowrap">
                    직접 공고 등록
                  </span>
                </button>
              </div>
            )}

            {/* --------------------  Bottom Bar (SVG) -------------------- */}
            <div className="relative w-[393px] h-[92px]">
              <img
                src="/rectangle-3-right.svg"
                alt="bottom bar"
                className="absolute left-0 bottom-0 w-[393px] h-[92px]"
              />

              {/* --------------------  + 버튼 + 글씨 -------------------- */}
              <div className="absolute -top-7 right-[30px] flex flex-col items-center gap-1.5 z-40">
                <button
                  type="button"
                  onClick={toggleMenu}
                  aria-label="공고 등록"
                  className={[
                    "w-[64px] h-[64px] rounded-full",
                    "bg-orange-500 text-black shadow-lg flex justify-center items-center",
                    "transition-all cursor-pointer",
                    isOpen ? "rotate-45" : "",
                  ].join(" ")}
                >
                  <svg
                    className="w-7 h-7"
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

                <span className="text-[15px] font-semibold text-black">
                  공고등록
                </span>
              </div>

              {/* --------------------  소일거리 / 홈 / 나의 정보 탭들 -------------------- */}
              <div className="absolute left-0 bottom-[34px] w-full flex justify-between pl-6 pr-[120px]">
                {/* 소일거리 */}
                <Item
                  active={isActive("/matchingpage")}
                  onClick={() => navigate("/matchingpage")}
                  label="소일거리"
                  icon={
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      className="w-full h-full"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
                      />
                    </svg>
                  }
                />

                {/* 홈 */}
                <Item
                  active={isActive("/main")}
                  onClick={() => navigate("/main")}
                  label="홈"
                  icon={
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      className="w-full h-full"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"
                      />
                    </svg>
                  }
                />

                {/* 나의 정보 */}
                <Item
                  active={isActive("/mypage")}
                  onClick={() => navigate("/mypage")}
                  label="나의 정보"
                  icon={
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      className="w-full h-full"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
                      />
                    </svg>
                  }
                />
              </div>
            </div>
          </div>
        </div>
      </nav>
    </>
  );
}