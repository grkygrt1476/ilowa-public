// src/pages/admin/AdminLogin.js
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  ADMIN_ACCESS_TOKEN_KEY,
  AuthAPI,
  apiFetch,
  parseApiError,
} from "../../utils/apiClient";

/** 전화번호 하이픈 포맷 (010-1234-5678 형태) */
function formatPhone(v) {
  const digits = (v || "").replace(/\D/g, "").slice(0, 11);
  if (digits.length < 4) return digits;
  if (digits.length < 8) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
  return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
}

export default function AdminLogin() {
  const nav = useNavigate();
  const [phone, setPhone] = useState("");
  const PIN_LENGTH = 4;
  const [pin, setPin] = useState(""); // 4자리 숫자
  const [showPin, setShowPin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [showUuidModal, setShowUuidModal] = useState(false);
  const [adminUuid, setAdminUuid] = useState("");
  const [copyFeedback, setCopyFeedback] = useState("");

  const onPhoneChange = (e) => setPhone(formatPhone(e.target.value));
  const onPinChange = (e) => {
    const onlyDigits = e.target.value.replace(/\D/g, "").slice(0, PIN_LENGTH);
    setPin(onlyDigits);
  };

  const canSubmit = () => {
    const digits = phone.replace(/\D/g, "");
    return digits.length >= 10 && pin.length === PIN_LENGTH;
  };

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      setLoading(true);
      const cleanPhone = phone.replace(/\D/g, "");
      const data = await AuthAPI.loginWithPin(cleanPhone, pin, {
        endpoint: "/api/v1/admin/login/pin",
        tokenKey: ADMIN_ACCESS_TOKEN_KEY,
      });

      if (!data?.access_token) {
        throw new Error("토큰 정보를 받지 못했어요.");
      }

      let adminUuidMessage = "";
      try {
        const profile = await apiFetch("/api/v1/users/me", {
          tokenKey: ADMIN_ACCESS_TOKEN_KEY,
        });
        if (profile?.user_id) {
          adminUuidMessage = `관리자 UUID: ${profile.user_id}\n\n.env 의 SEED_JOBS_OWNER_ID= 값으로 붙여 넣어주세요.`;
        }
      } catch (profileErr) {
        console.warn("관리자 UUID 확인 실패:", profileErr);
      }

      if (adminUuidMessage) {
        const uuid = (adminUuidMessage.match(/[0-9a-fA-F-]{36}/) || [])[0] || "";
        setAdminUuid(uuid);
      } else if (data?.user_id) {
        setAdminUuid(data.user_id);
      }
      setShowUuidModal(true);
    } catch (e2) {
      setErr(parseApiError(e2, "전화번호 또는 PIN을 확인해 주세요."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm bg-white rounded-2xl p-6 shadow-md">
        <h1 className="text-2xl font-bold text-gray-900 text-center">관리자 로그인</h1>
        <p className="text-gray-500 text-center mt-1 mb-6">공고 승인용</p>

        {err && (
          <div className="mb-4 p-3 rounded-xl bg-rose-50 text-rose-700 text-sm">
            {err}
          </div>
        )}

        <form onSubmit={submit} className="space-y-4">
          {/* 전화번호 */}
          <div>
            <label className="block text-sm text-gray-600 mb-1">전화번호</label>
            <input
              type="tel"
              inputMode="numeric"
              pattern="[0-9\-]*"
              placeholder="010-0000-0000"
              value={phone}
              onChange={onPhoneChange}
              className="w-full border rounded-xl px-3 py-3"
              required
            />
          </div>

          {/* PIN */}
          <div>
            <label className="block text-sm text-gray-600 mb-1">PIN (4자리)</label>
            <div className="relative">
              <input
                type={showPin ? "text" : "password"}
                inputMode="numeric"
                pattern="\d{4}"
                placeholder="••••"
                value={pin}
                onChange={onPinChange}
                className="w-full border rounded-xl px-3 py-3 pr-20 tracking-widest"
                required
              />
              <button
                type="button"
                onClick={() => setShowPin((s) => !s)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-sm text-gray-500 underline"
              >
                {showPin ? "숨기기" : "표시"}
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">숫자만 입력하세요.</p>
          </div>

          {/* 제출 */}
          <button
            type="submit"
            disabled={loading || !canSubmit()}
            className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold text-lg py-3 rounded-xl disabled:opacity-50"
          >
            {loading ? "로그인 중..." : "로그인"}
          </button>

          <button
            type="button"
            onClick={() => nav(-1)}
            className="w-full bg-gray-100 text-gray-700 font-semibold py-3 rounded-xl"
          >
            취소
          </button>
        </form>
      </div>

      {/* 추가된 하단 버튼 */}
      <div className="mt-6 text-center">
        <button
          type="button"
          onClick={() => nav("/approval")}
          className="text-sm underline text-gray-600 hover:text-gray-900"
        >
          관리자용 공고 승인 페이지
        </button>
      </div>

      {showUuidModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-3">관리자 UUID</h2>
            <p className="text-sm text-gray-600 mb-4">
              아래 값을 복사하여 <code className="px-1 py-0.5 bg-gray-100 rounded text-xs">SEED_JOBS_OWNER_ID</code> 에
              붙여 넣어 주세요.
            </p>
            <div className="bg-gray-100 rounded-xl p-4 font-mono text-sm break-all mb-3">
              {adminUuid || "UUID를 가져오지 못했습니다. /api/v1/users/me 확인 필요"}
            </div>
            <button
              type="button"
              onClick={() => {
                if (!adminUuid) return;
                navigator.clipboard
                  .writeText(adminUuid)
                  .then(() => {
                    setCopyFeedback("복사되었습니다!");
                    setTimeout(() => setCopyFeedback(""), 2000);
                  })
                  .catch(() => setCopyFeedback("복사에 실패했습니다."));
              }}
              className="w-full bg-gray-900 text-white py-3 rounded-xl mb-2"
              disabled={!adminUuid}
            >
              {copyFeedback || "UUID 복사"}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowUuidModal(false);
                nav("/matchingpage", { replace: true });
              }}
              className="w-full bg-orange-500 text-white py-3 rounded-xl"
            >
              확인하고 이동
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
