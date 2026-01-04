// src/pages/register/RegisterFlow.js
import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";

// 백엔드 API의 기본 URL
const BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:8000";

/* ----------------------------- 공통 토스트 ----------------------------- */
function Toast({ message, onClose, duration = 2500, type = "error" }) {
  useEffect(() => {
    const t = setTimeout(onClose, duration);
    return () => clearTimeout(t);
  }, [onClose, duration]);

  const bgColor = type === "error" ? "bg-red-500" : "bg-green-600";
  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50">
      <div className={`px-4 py-3 rounded-xl shadow-lg ${bgColor} text-white font-semibold`}>
        {message}
      </div>
    </div>
  );
}

/* ----------------------------- 공통 헤더 ----------------------------- */
// total(총 단계 수)을 받아서 진행바를 계산 (회원가입은 4단계)
function StepHeader({ step, total = 4, onBack }) {
  return (
    <>
      <header className="bg-white border-b px-6 py-7">
        <div className="max-w-md mx-auto flex items-center justify-between">
          <button onClick={onBack} className="p-2" type="button">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-xl font-bold">회원가입</h1>
          <div className="w-10 h-7"></div>
        </div>
      </header>

      <div className="max-w-md mx-auto px-4 py-4">
        <div className="flex gap-1">
          {Array.from({ length: total }, (_, i) => i + 1).map((s) => (
            <div key={s} className={`flex-1 h-1.5 rounded ${s <= step ? "bg-orange-500" : "bg-gray-200"}`} />
          ))}
        </div>
        <p className="text-sm text-gray-500 mt-2 text-center">{step}/{total} 단계</p>
      </div>
    </>
  );
}

/* ----------------------------- Step 1: 전화번호 ----------------------------- */
function Step1PhoneNumber({ onNext, onBack, setParentPhone, setParentError }) {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [loading, setLoading] = useState(false);

  const handlePhoneChange = (e) => {
    const value = e.target.value.replace(/[^0-9]/g, "").slice(0, 11);
    setPhoneNumber(value);
  };

  const formatPhoneNumber = (value) => {
    if (value.length <= 3) return value;
    if (value.length <= 7) return `${value.slice(0, 3)}-${value.slice(3)}`;
    return `${value.slice(0, 3)}-${value.slice(3, 7)}-${value.slice(7, 11)}`;
    };

  const requestOtp = async () => {
    if (phoneNumber.length !== 11) return;
    setLoading(true);
    setParentError(null);
    try {
      // REG_01: 전화번호 유효성 확인
      const phoneReq = await fetch(`${BASE_URL}/api/v1/auth/register/phone`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: phoneNumber }),
      });
      if (!phoneReq.ok) {
        setParentError("번호 확인 중 오류가 발생했습니다.");
        setLoading(false);
        return;
      }
      // REG_02: OTP 발송
      const otpRes = await fetch(`${BASE_URL}/api/v1/auth/otp/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: phoneNumber, purpose: "register" }),
      });
      if (!otpRes.ok) {
        const errorData = await otpRes.json().catch(() => ({}));
        setParentError(errorData.detail || "인증번호 발송에 실패했습니다.");
        return;
      }
      setParentPhone(phoneNumber);
      onNext();
    } catch (e) {
      console.error(e);
      setParentError("서버 연결 오류. 잠시 후 다시 시도해주세요.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <StepHeader step={1} total={4} onBack={onBack} />
      <main className="max-w-md mx-auto px-6 py-12">
        <h2 className="text-3xl font-bold mb-4">전화번호를<br />입력해주세요</h2>
        <p className="text-gray-600 text-lg mb-12">간편하게 전화번호로 가입하세요 !</p>
        <div className="mb-4">
          <input
            type="tel"
            value={formatPhoneNumber(phoneNumber)}
            onChange={handlePhoneChange}
            placeholder="010-0000-0000"
            maxLength={13}
            className="w-full px-6 py-5 text-2xl border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          />
        </div>
        <button
          type="button"
          onClick={requestOtp}
          disabled={phoneNumber.length !== 11 || loading}
          className="w-full bg-orange-500 text-white font-bold text-xl py-5 rounded-xl disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-orange-600 transition flex items-center justify-center"
        >
          {loading ? "전송 중..." : "다음"}
        </button>
      </main>
    </div>
  );
}

/* ----------------------------- Step 2: OTP ----------------------------- */
function Step2OTP({ onNext, onBack, phone, setParentError, setSetupToken }) {
  const [code, setCode] = useState("");
  const [timer, setTimer] = useState(180);
  const [loading, setLoading] = useState(false);

  // 시연용 우회 코드
  const DUMMY_CODE = "000000";

  useEffect(() => {
    const id = setInterval(() => setTimer((t) => (t > 0 ? t - 1 : 0)), 1000);
    return () => clearInterval(id);
  }, []);

  const handleCodeChange = (e) => {
    const value = e.target.value.replace(/[^0-9]/g, "").slice(0, 6);
    setCode(value);
  };

  const verifyOtp = async () => {
    if (code.length !== 6) return;
    setLoading(true);
    setParentError(null);
    try {
      // REG_02: OTP 검증
      const response = await fetch(`${BASE_URL}/api/v1/auth/otp/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: phone, code, purpose: "register" }),
      });
      const data = await response.json().catch(() => ({}));
      if (response.ok) {
        if (data.setup_token) {
          setSetupToken(data.setup_token);
          onNext();
        } else {
          setParentError("토큰 정보 누락. 다시 시도해 주세요.");
        }
      } else {
        setParentError(data.detail || "인증번호가 일치하지 않거나 만료되었습니다.");
      }
    } catch (e) {
      console.error(e);
      setParentError("서버 연결 오류. 잠시 후 다시 시도해주세요.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <StepHeader step={2} total={4} onBack={onBack} />
      <main className="max-w-md mx-auto px-6 py-12">
        <h2 className="text-3xl font-bold mb-4">인증번호를<br />입력해주세요</h2>
        <p className="text-gray-600 text-lg mb-12 font-bold text-red-500">[시연용] 인증번호는 '{DUMMY_CODE}'를 입력하세요.</p>
        <div className="mb-6">
          <input
            type="text"
            value={code}
            onChange={handleCodeChange}
            placeholder="000000"
            maxLength={6}
            className="w-full px-6 py-5 text-3xl text-center tracking-widest border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          />
          <p className="text-lg text-orange-500 mt-3 text-right font-medium">
            {Math.floor(timer / 60)}:{String(timer % 60).padStart(2, "0")}
          </p>
        </div>

        <button className="w-full bg-gray-100 text-gray-700 font-bold text-lg py-4 rounded-xl hover:bg-gray-200 mb-3" disabled={loading} type="button">
          인증번호 다시 받기
        </button>

        <button
          type="button"
          onClick={verifyOtp}
          disabled={code.length !== 6 || loading}
          className="w-full bg-orange-500 text-white font-bold text-xl py-5 rounded-xl disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-orange-600 transition"
        >
          {loading ? "인증 중..." : "인증하기"}
        </button>
      </main>
    </div>
  );
}

/* ----------------------------- Step 3: 약관 ----------------------------- */
function Step3Terms({ onNext, onBack, phone, setParentError }) {
  const [allAgreed, setAllAgreed] = useState(false);
  const [serviceAgree, setServiceAgree] = useState(false);
  const [privacyAgree, setPrivacyAgree] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setAllAgreed(serviceAgree && privacyAgree);
  }, [serviceAgree, privacyAgree]);

  const handleAllAgree = () => {
    const v = !allAgreed;
    setAllAgreed(v);
    setServiceAgree(v);
    setPrivacyAgree(v);
  };

  const submitAgreements = async () => {
    if (!serviceAgree || !privacyAgree) return;
    setLoading(true);
    setParentError(null);
    try {
      // REG_03: 약관 동의
      const response = await fetch(`${BASE_URL}/api/v1/auth/register/agreements`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone_number: phone,
          agreements: { terms: serviceAgree, privacy: privacyAgree },
        }),
      });
      if (response.ok) {
        onNext();
      } else {
        setParentError("약관 동의 처리 중 오류가 발생했습니다.");
      }
    } catch (e) {
      setParentError("서버 연결 오류. 잠시 후 다시 시도해주세요.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <StepHeader step={3} total={4} onBack={onBack} />
      <main className="max-w-md mx-auto px-6 py-12">
        <h2 className="text-3xl font-bold mb-4">약관에<br />동의해주세요</h2>
        <p className="text-gray-600 text-lg mb-12">서비스 이용을 위해 필요해요</p>

        <div className="space-y-4 mb-8">
          <div
            onClick={handleAllAgree}
            className="flex items-center gap-4 p-5 border-2 border-orange-500/10 rounded-xl bg-orange-50 cursor-pointer"
          >
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center ${
                allAgreed ? "bg-orange-500" : "bg-white border-2 border-gray-300"
              }`}
            >
              {allAgreed && (
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <span className="text-lg font-bold">전체 동의하기</span>
          </div>

          <div className="h-px bg-gray-200 my-6"></div>

          <div
            onClick={() => setServiceAgree(!serviceAgree)}
            className="flex items-center gap-4 p-5 border-2 border-gray-200 rounded-xl cursor-pointer"
          >
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center ${
                serviceAgree ? "bg-orange-500" : "bg-white border-2 border-gray-300"
              }`}
            >
              {serviceAgree && (
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <span className="text-lg">[필수] 서비스 이용약관</span>
          </div>

          <div
            onClick={() => setPrivacyAgree(!privacyAgree)}
            className="flex items-center gap-4 p-5 border-2 border-gray-200 rounded-xl cursor-pointer"
          >
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center ${
                privacyAgree ? "bg-orange-500" : "bg-white border-2 border-gray-300"
              }`}
            >
              {privacyAgree && (
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <span className="text-lg">[필수] 개인정보 처리방침</span>
          </div>
        </div>

        <button
          type="button"
          onClick={submitAgreements}
          disabled={!serviceAgree || !privacyAgree || loading}
          className="w-full bg-orange-500 text-white font-bold text-xl py-5 rounded-xl disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-orange-600 transition"
        >
          {loading ? "처리 중..." : "다음"}
        </button>
      </main>
    </div>
  );
}

/* ----------------------------- Step 4: PIN + 가입 최종 ----------------------------- */
function Step4PIN({ onBack, phone, setupToken, setParentError }) {
  const navigate = useNavigate();
  const [pin, setPin] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [pinConfirm, setPinConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const handlePinChange = (e) => {
    const value = e.target.value.replace(/[^0-9]/g, "").slice(0, 4);
    if (!showConfirm) {
      setPin(value);
      if (value.length === 4) {
        setTimeout(() => setShowConfirm(true), 300);
      }
    } else {
      setPinConfirm(value);
    }
  };

  const handleSubmit = async () => {
    if (loading) return;
    if (pin !== pinConfirm) {
      setParentError("PIN이 일치하지 않습니다. 다시 시도하세요.");
      setShowConfirm(false);
      setPinConfirm("");
      return;
    }
    setLoading(true);
    setParentError(null);
    try {
      // REG_04: 최종 가입
      const response = await fetch(`${BASE_URL}/api/v1/auth/register/pin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone_number: phone,
          pin,
          confirm_pin: pinConfirm,
          setup_token: setupToken,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (response.ok && data.access_token) {
        // 토큰 저장
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        // ✅ 회원가입 완료 → 온보딩 시작
        navigate("/onboarding/nickname", { replace: true });
        return;
      } else {
        setParentError(data.detail || "가입 처리 중 오류가 발생했습니다. 다시 시도해 주세요.");
        setShowConfirm(false);
        setPinConfirm("");
      }
    } catch (e) {
      console.error(e);
      setParentError("서버 연결에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <StepHeader step={4} total={4} onBack={onBack} />
      <main className="max-w-md mx-auto px-6 py-12">
        <h2 className="text-3xl font-bold mb-4">
          {!showConfirm ? "PIN을\n설정해주세요" : "PIN을\n다시 입력해주세요"}
        </h2>
        <p className="text-gray-600 text-lg mb-12">
          {!showConfirm ? "간편하게 로그인할 수 있어요" : "같은 번호를 한 번 더 입력하세요"}
        </p>
        <div className="mb-8">
          <input
            type="password"
            value={!showConfirm ? pin : pinConfirm}
            onChange={handlePinChange}
            placeholder="••••"
            maxLength={4}
            className="w-full px-6 py-5 text-4xl text-center tracking-widest border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            disabled={loading}
          />
        </div>
        {showConfirm && (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={pinConfirm.length !== 4 || loading}
            className="w-full bg-orange-500 text-white font-bold text-xl py-5 rounded-xl disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-orange-600 transition flex items-center justify-center"
          >
            {loading ? "가입 처리 중..." : "완료"}
          </button>
        )}
      </main>
    </div>
  );
}

/* ----------------------------- RegisterFlow 본체 ----------------------------- */
export default function RegisterFlow() {
  const [phone, setPhone] = useState("");
  const [setupToken, setSetupToken] = useState("");
  const [step, setStep] = useState(1);
  const [error, setError] = useState(null);

  const navigate = useNavigate();

  const onNext = useCallback(() => setStep((s) => Math.min(4, s + 1)), []);
  const onBack = useCallback(() => {
    setError(null);
    if (step > 1) setStep((s) => s - 1);
    else navigate("/");
  }, [step, navigate]);

  return (
    <div className="min-h-screen bg-white">
      {/* 공통 에러 토스트 */}
      {error && <Toast message={error} onClose={() => setError(null)} type="error" />}

      {step === 1 && (
        <Step1PhoneNumber
          onNext={onNext}
          onBack={onBack}
          setParentPhone={setPhone}
          setParentError={setError}
        />
      )}
      {step === 2 && (
        <Step2OTP
          onNext={onNext}
          onBack={onBack}
          phone={phone}
          setParentError={setError}
          setSetupToken={setSetupToken}
        />
      )}
      {step === 3 && (
        <Step3Terms
          onNext={onNext}
          onBack={onBack}
          phone={phone}
          setParentError={setError}
        />
      )}
      {step === 4 && (
        <Step4PIN
          onBack={onBack}
          phone={phone}
          setupToken={setupToken}
          setParentError={setError}
        />
      )}
    </div>
  );
}
