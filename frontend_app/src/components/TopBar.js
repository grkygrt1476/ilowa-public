// src/components/TopBar.js
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { NotificationsAPI } from "../utils/apiClient";

export default function TopBar(props) {
  const navigate = useNavigate();

  const {
    logoSrc = "/logo.png",
    showNotification = true,
    nickname = "",
    statusText = "",
  } = props;

  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await NotificationsAPI.list().catch(() => ({ items: [] }));
        if (!active) return;
        const list = data?.items || data?.notifications || [];
        setUnreadCount(list.filter((item) => !item.is_read).length);
      } catch {
        if (active) setUnreadCount(0);
      }
    };
    load();
    const interval = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="fixed top-0 left-0 right-0 bg-white border-b border-orange-100 z-50">
      {/* ⭐ 높이를 강제로 맞추고 위아래 여백 제거 */}
      <div className="h-[80px] w-full flex items-center px-4">

        {/* ⬅ 닉네임 + 상태 (위아래 여백 제거) */}
        <div className="flex left-10 flex-col justify-center leading-tight -mt-[2px] ml-4">
          <p className="text-[15px] font-bold text-gray-900">
            {nickname ? `${nickname}님 👋` : "로딩 중…"}
          </p>

          <p className="inline-flex left-10 items-center mt-[2px] px-2 py-[1px] 
                        rounded-full bg-orange-50 text-[10px] 
                        text-customorange font-semibold border border-orange-200">
            {statusText || "소일거리 확인 중"}
          </p>
        </div>

        {/* 가운데 로고 (정확히 수직 중앙, 위아래 여백 없음) */}
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center">
          <img
            src={logoSrc}
            alt="ILOWA"
            className="h-14 w-14 object-contain"
          />
        </div>

        {/* ➡ 알림 버튼 */}
        {showNotification ? (
          <button
            onClick={() => navigate("/notification")}
            className="relative ml-auto mr-3 px-3 py-2 text-lg font-extrabold text-orange-500 hover:scale-105 transition"
            style={{
              textShadow: `
                -1px -1px 0 #000,
                 1px -1px 0 #000,
                -1px  1px 0 #000,
                 1px  1px 0 #000
              `,
            }}
          >
            알림
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[20px] px-1 py-[2px] rounded-full bg-red-500 text-white text-xs font-bold">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </button>
        ) : (
          <div className="ml-auto w-[50px]" />
        )}
      </div>
    </header>
  );
}
