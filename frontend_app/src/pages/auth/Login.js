// src/pages/auth/Login.js
import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { AuthAPI, parseApiError } from "../../utils/apiClient";

/** 문자열 보장 유틸 */
function toText(x) {
  if (x == null) return "";
  if (typeof x === "string") return x;
  if (typeof x === "number" || typeof x === "boolean") return String(x);
  if (typeof x === "object") {
    if (typeof x.message === "string") return x.message;
    if (typeof x.detail === "string") return x.detail;
    if (Array.isArray(x.detail) && x.detail.length) return toText(x.detail[0]);
    try { return JSON.stringify(x); } catch { return "오류가 발생했습니다."; }
  }
  return "오류가 발생했습니다.";
}

/** 안전한 Toast */
function Toast({ message = "", onClose = () => {}, duration = 2500, type = "success" }) {
  useEffect(() => {
    if (typeof onClose !== "function") return;
    const t = setTimeout(() => onClose(), duration);
    return () => clearTimeout(t);
  }, [onClose, duration]);

  const text = toText(message);
  if (!text) return null;

  const bg = type === "error" ? "bg-red-500" : "bg-green-600";
  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50">
      <div className={`px-4 py-3 rounded-xl shadow-lg ${bg} text-white font-semibold`}>
        {String(text)}
      </div>
    </div>
  );
}

const formatPhone = (v = "") => {
  const value = v.replace(/[^0-9]/g, "").slice(0, 11);
  if (value.length <= 3) return value;
  if (value.length <= 7) return `${value.slice(0, 3)}-${value.slice(3)}`;
  return `${value.slice(0, 3)}-${value.slice(3, 7)}-${value.slice(7, 11)}`;
};

export default function Login() {
  const location = useLocation();
  const navigate = useNavigate();

  // 회원가입에서 전달된 초기값들
  const initialPhone = location.state?.phone || "";
  const showRegisterToast = location.state?.toast === "register_complete";

  const [phone, setPhone] = useState(initialPhone.replace(/-/g, "")); // 숫자만
  const [pin, setPin] = useState("");
  const [showToast, setShowToast] = useState(showRegisterToast);
  const [toastMessage, setToastMessage] = useState(showRegisterToast ? "회원가입이 완료되었습니다!" : "");
  const [toastType, setToastType] = useState("success");
  const [loading, setLoading] = useState(false);

  const handlePinChange = (e) => {
    const v = e.target.value.replace(/[^0-9]/g, "").slice(0, 4);
    setPin(v);
  };
  const handleToastClose = () => setShowToast(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;

    const cleanPhone = phone.replace(/[^0-9]/g, "");
    if (cleanPhone.length !== 11 || pin.length !== 4) {
      setToastMessage("전화번호(11자리)와 PIN(4자리)을 정확히 입력하세요.");
      setToastType("error");
      setShowToast(true);
      return;
    }

    setLoading(true);
    setShowToast(false);

    try {
      const data = await AuthAPI.loginWithPin(cleanPhone, pin);
      setToastMessage("로그인 성공!");
      setToastType("success");
      setShowToast(true);
      if (data?.access_token) {
        setTimeout(() => navigate("/main", { replace: true }), 400);
      }
    } catch (err) {
      console.error("[login fetch error]", err);
      setToastMessage(parseApiError(err, "로그인 실패 (필드명 불일치 가능)"));
      setToastType("error");
      setShowToast(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      {showToast && <Toast message={toastMessage} onClose={handleToastClose} type={toastType} />}

      <header className="bg-white border-b px-4 py-4">
        <div className="max-w-md mx-auto flex items-center justify-between">
          <button onClick={() => navigate(-1)} className="p-2" aria-label="뒤로가기">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-lg font-bold">로그인</h1>
          <div className="w-10" />
        </div>
      </header>

      <main className="max-w-md mx-auto px-6 py-12">
        <h2 className="text-3xl font-bold mb-4">
          전화번호와<br />PIN으로 로그인
        </h2>
        <p className="text-gray-600 text-lg mb-10">가입 시 입력한 정보로 로그인하세요</p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 전화번호 */}
          <div>
            <label className="block text-lg font-medium mb-3">전화번호</label>
            <input
              type="tel"
              value={formatPhone(phone)}
              onChange={(e) => setPhone(e.target.value.replace(/[^0-9]/g, ""))}
              placeholder="010-0000-0000"
              className="w-full px-6 py-5 text-xl border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              disabled={loading}
            />
            <p className="text-sm text-gray-500 mt-2">가입했던 번호(숫자 11자리)를 입력하세요</p>
          </div>

          {/* PIN */}
          <div>
            <label className="block text-lg font-medium mb-3">PIN (4자리)</label>
            <input
              type="password"
              value={pin}
              onChange={handlePinChange}
              inputMode="numeric"
              placeholder="••••"
              maxLength={4}
              className="w-full px-6 py-5 text-4xl text-center tracking-widest border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={phone.replace(/[^0-9]/g, "").length !== 11 || pin.length !== 4 || loading}
            className="w-full bg-orange-500 text-white font-bold text-xl py-5 rounded-xl disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-orange-600 transition flex items-center justify-center"
          >
            {loading ? (
              <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              "로그인"
            )}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-gray-500">
          <button className="underline" onClick={() => { /* TODO: OTP 로그인 화면 */ }}>
            PIN을 잊으셨나요?
          </button>
        </div>
      </main>
    </div>
  );
}
