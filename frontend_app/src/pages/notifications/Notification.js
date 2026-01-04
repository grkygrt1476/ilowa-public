import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { NotificationsAPI } from "../../utils/apiClient";

export default function Notification() {
  const nav = useNavigate();

  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const notifData = await NotificationsAPI.list();
      const notifList = Array.isArray(notifData?.items) ? [...notifData.items] : [];
      notifList.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setNotifications(notifList);
    } catch (e) {
      console.error("알림을 불러오지 못했어요:", e);
      setError("알림을 불러오지 못했어요. 잠시 후 다시 시도해주세요.");
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleGoMain = () => {
    nav("/main", { replace: true });
  };

  const markAsRead = async (notifId) => {
    try {
      await NotificationsAPI.markRead(notifId, true);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notifId ? { ...n, is_read: true } : n))
      );
    } catch (e) {
      console.error("알림 읽음 처리 실패:", e);
      setError("알림 읽음 처리에 실패했어요.");
    }
  };

  const handleNotificationClick = async (notif) => {
    try {
      await markAsRead(notif.id);
      if (notif.link) {
        nav(notif.link);
      }
    } catch (e) {
      console.error("알림 이동 실패:", e);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "방금 전";
    if (minutes < 60) return `${minutes}분 전`;
    if (hours < 24) return `${hours}시간 전`;
    if (days < 7) return `${days}일 전`;

    return date.toLocaleDateString("ko-KR", {
      month: "short",
      day: "numeric"
    });
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case "job_application": return "🧑‍💼";
      case "application_result": return "📬";
      case "post_submitted": return "📝";
      case "match_event": return "🎉";
      case "review_result": return "✅";
      default: return "🔔";
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-4 border-orange-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-4 text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ✅ 요청한 헤더 추가 */}
      <header className="px-6 py-7 flex items-center justify-between border-b">
        <button
          type="button"
          className="p-2"
          onClick={() => nav(-1)}
        >
          <ChevronLeft className="w-6 h-6" />
        </button>

        <h1 className="absolute left-1/2 -translate-x-1/2 text-xl font-bold">
          알림
        </h1>

        <div className="w-10" />
        <button
          onClick={handleGoMain}
          className="text-black font-medium text-sm"
        >
          뒤로가기
        </button>
      </header>

      {/* 본문 */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* 미읽은 알림 */}
        {error && (
          <div className="bg-rose-50 text-rose-600 border border-rose-200 rounded-xl px-4 py-3 mb-4">
            {error}
          </div>
        )}

        {notifications.filter(n => !n.is_read).length > 0 && (
          <div className="bg-white rounded-2xl shadow-md p-6 mb-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              🔔 새 알림
              <span className="bg-orange-600 text-white text-xs px-2 py-1 rounded-full">
                {notifications.filter(n => !n.is_read).length}
              </span>
            </h2>
            <div className="space-y-3">
              {notifications.filter(n => !n.is_read).map((notif) => (
                <div
                  key={notif.id}
                  className="p-4 bg-orange-50 rounded-xl border border-orange-200"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex gap-3 flex-1">
                      <span className="text-2xl">{getNotificationIcon(notif.type)}</span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="text-gray-900 font-semibold">{notif.title}</p>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-red-500 text-white">
                            새로운 메시지
                          </span>
                        </div>
                        <p className="text-gray-700 text-sm">{notif.message}</p>
                      </div>
                    </div>
                    <span className="text-xs text-gray-500 whitespace-nowrap">
                      {formatDate(notif.created_at)}
                    </span>
                  </div>
                  <div className="mt-3 text-right">
                    <button
                      onClick={() => handleNotificationClick(notif)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold text-white bg-orange-500 rounded-full hover:bg-orange-600"
                    >
                      확인
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 읽은 알림 */}
        {notifications.filter(n => n.is_read).length > 0 && (
          <div className="bg-white rounded-2xl shadow-md p-6 mb-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">이전 알림</h2>
            <div className="space-y-2">
              {notifications.filter(n => n.is_read).map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  className="p-4 bg-gray-50 rounded-xl cursor-pointer hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex gap-3 flex-1">
                      <span className="text-xl opacity-50">{getNotificationIcon(notif.type)}</span>
                      <div className="flex-1">
                        <p className="text-gray-700 font-medium mb-1">{notif.title}</p>
                        <p className="text-gray-600 text-sm">{notif.message}</p>
                      </div>
                    </div>
                    <span className="text-xs text-gray-400 whitespace-nowrap">
                      {formatDate(notif.created_at)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {notifications.length === 0 && (
          <div className="bg-white rounded-2xl shadow-md p-12 text-center text-gray-500">
            아직 도착한 알림이 없습니다.
          </div>
        )}
      </div>
    </div>
  );
}
