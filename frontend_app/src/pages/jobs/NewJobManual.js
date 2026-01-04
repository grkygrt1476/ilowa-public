// src/pages/jobs/NewJobManual.js
import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  MapPin,
  Calendar,
  Clock,
  Users,
  DollarSign,
  User,
  FileText,
} from "lucide-react";

import {
  JobsAPI,
  parseApiError,
  getStoredToken,
} from "../../utils/apiClient";

// ── 작은 UI 컴포넌트
function Card({ children, className = "" }) {
  return (
    <div
      className={`bg-white rounded-2xl border border-gray-100 shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}
function Pill({ children, active }) {
  return (
    <span
      className={[
        "px-3 py-2 rounded-full text-sm font-medium transition",
        active ? "bg-orange-500 text-white" : "bg-gray-100 text-gray-700",
      ].join(" ")}
    >
      {children}
    </span>
  );
}

export default function NewJobManual() {
  const nav = useNavigate();

  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");

  const [formData, setFormData] = useState({
    title: "",
    participants: 1,
    hourly_wage: 15000,
    place: "",
    address: "",
    work_days: [],
    start_time: "09:00",
    end_time: "12:00",
    client: "",
    description: "",
  });

  const weekDays = useMemo(
    () => ["월", "화", "수", "목", "금", "토", "일"],
    []
  );

  const handleChange = (field, value) => {
    setErrMsg("");
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const toggleWorkDay = (day) => {
    setErrMsg("");
    setFormData((prev) => ({
      ...prev,
      work_days: prev.work_days.includes(day)
        ? prev.work_days.filter((d) => d !== day)
        : [...prev.work_days, day],
    }));
  };

  const handleBack = () => {
    if (window.history.length > 1) nav(-1);
    else nav("/");
  };

  const validate = () => {
    if (!formData.title?.trim()) return "공고 제목을 입력해주세요.";
    if (!formData.place?.trim())
      return "근무 장소(동/행정동)를 입력해주세요.";
    if (!formData.address?.trim()) return "상세 주소를 입력해주세요.";
    if (
      !Array.isArray(formData.work_days) ||
      formData.work_days.length === 0
    )
      return "근무 요일을 1개 이상 선택해주세요.";
    if (!formData.start_time || !formData.end_time)
      return "근무 시간을 입력해주세요.";
    if (formData.start_time >= formData.end_time)
      return "근무 시작시간이 종료시간보다 빠르거나 같아서는 안돼요.";
    if (
      !Number.isFinite(Number(formData.hourly_wage)) ||
      Number(formData.hourly_wage) <= 0
    )
      return "시급을 올바르게 입력해주세요.";
    if (
      !Number.isInteger(Number(formData.participants)) ||
      Number(formData.participants) < 1
    )
      return "모집인원은 1명 이상이어야 합니다.";
    if (!formData.description?.trim())
      return "상세 설명을 입력해주세요.";
    return "";
  };

  const normalizeForApi = () => {
    const dayMap = {
      월: "MON",
      화: "TUE",
      수: "WED",
      목: "THU",
      금: "FRI",
      토: "SAT",
      일: "SUN",
    };
    return {
      title: formData.title.trim(),
      participants: Number(formData.participants),
      hourly_wage: Number(formData.hourly_wage),
      place: formData.place.trim(),
      address: formData.address.trim(),
      work_days: formData.work_days.map((d) => dayMap[d] ?? d),
      start_time: formData.start_time,
      end_time: formData.end_time,
      client: formData.client?.trim() || null,
      description: formData.description.trim(),
    };
  };

  const handleSubmit = async () => {
    setErrMsg("");
    const v = validate();
    if (v) {
      setErrMsg(v);
      return;
    }

    const payload = normalizeForApi();

    setLoading(true);
    try {
      const token = getStoredToken();
      if (!token) {
        setErrMsg("로그인이 필요합니다. 먼저 로그인해주세요.");
        setLoading(false);
        return;
      }

      const data = await JobsAPI.create(payload);
      if (data?.id) nav(`/jobs/${data.id}`, { replace: true });
      else nav("/jobs", { replace: true });
    } catch (err) {
      setErrMsg(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F8FA]">
      {/* 헤더*/}
      <header className="fixed top-0 left-0 right-0 z-40 h-[72px] bg-white/90 backdrop-blur border-b">
        <div className="max-w-lg mx-auto h-full px-5 flex items-center justify-between">
            {/* 🔙 뒤로가기 버튼 */}
            <button
            onClick={handleBack}
            className="w-12 h-12 rounded-full grid place-items-center hover:bg-gray-100"
            aria-label="뒤로"
            >
            <svg
                className="w-7 h-7 text-gray-800"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
            >
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
            </button>

            {/* 타이틀 */}
            <h1 className="text-[22px] font-extrabold tracking-tight text-gray-900">
            공고 등록
            </h1>

            {/* ✅ 둥근 직사각형 '등록' 버튼 */}
            <button
            onClick={handleSubmit}
            disabled={loading}
            className={`min-w-[90px] h-[40px] rounded-full px-5 font-semibold text-[17px] 
                ${loading
                ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                : "bg-orange-500 text-white hover:bg-orange-600 active:scale-95 transition"
                }`}
            aria-label="등록하기"
            >
            {loading ? "등록 중..." : "등록"}
            </button>
        </div>
        </header>

      <main className="max-w-lg mx-auto p-5 pb-[140px] space-y-5 text-[18px] leading-7 pt-[calc(72px+env(safe-area-inset-top))]">
        {/* 에러 박스 */}
        {errMsg && (
          <Card className="border-red-200">
            <div className="px-4 py-3 text-red-700">{errMsg}</div>
          </Card>
        )}

        {/* 공고 제목 (아이콘 추가됨) */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-5 h-5 text-orange-500" />
            <h3 className="text-base font-semibold text-gray-800">
              공고 제목
            </h3>
          </div>
          <input
            type="text"
            value={formData.title}
            onChange={(e) => handleChange("title", e.target.value)}
            placeholder="예: 아파트 경비원 구합니다"
            className="w-full px-4 py-3 border rounded-xl text-[15px] focus:outline-none focus:ring-2 focus:ring-orange-200 border-gray-200"
          />
        </Card>

        {/* 근무 장소 */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <MapPin className="w-5 h-5 text-orange-500" />
            <h3 className="text-base font-semibold text-gray-800">근무 장소</h3>
          </div>
          <div className="space-y-3">
            <input
              type="text"
              value={formData.place}
              onChange={(e) => handleChange("place", e.target.value)}
              placeholder="예: 성동구 행당동"
              className="w-full px-4 py-3 border rounded-xl text-[15px] focus:outline-none focus:ring-2 focus:ring-orange-200 border-gray-200"
            />
            <input
              type="text"
              value={formData.address}
              onChange={(e) => handleChange("address", e.target.value)}
              placeholder="상세 주소"
              className="w-full px-4 py-3 border rounded-xl text-[15px] focus:outline-none focus:ring-2 focus:ring-orange-200 border-gray-200"
            />
          </div>
        </Card>

        {/* 근무 요일 */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Calendar className="w-5 h-5 text-orange-500" />
            <h3 className="text-base font-semibold text-gray-800">
              근무 요일
            </h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {weekDays.map((day) => {
              const active = formData.work_days.includes(day);
              return (
                <button
                  key={day}
                  type="button"
                  onClick={() => toggleWorkDay(day)}
                  className="active:scale-95"
                >
                  <Pill active={active}>{day}</Pill>
                </button>
              );
            })}
          </div>
        </Card>

        {/* 근무 시간 */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-5 h-5 text-orange-500" />
            <h3 className="text-base font-semibold text-gray-800">근무 시간</h3>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="time"
              value={formData.start_time}
              onChange={(e) => handleChange("start_time", e.target.value)}
              className="flex-1 px-4 py-3 border rounded-xl text-[15px] focus:outline-none focus:ring-2 focus:ring-orange-200 border-gray-200"
            />
            <span className="text-gray-400 font-bold">~</span>
            <input
              type="time"
              value={formData.end_time}
              onChange={(e) => handleChange("end_time", e.target.value)}
              className="flex-1 px-4 py-3 border rounded-xl text-[15px] focus:outline-none focus:ring-2 focus:ring-orange-200 border-gray-200"
            />
          </div>
        </Card>

        {/* 시급 & 모집인원 */}
        <div className="grid grid-cols-2 gap-4">
          <Card className="p-4">
            <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
              <DollarSign className="w-5 h-5 text-orange-500" />
              시급
            </label>
            <input
              type="number"
              value={formData.hourly_wage}
              onChange={(e) =>
                handleChange("hourly_wage", parseInt(e.target.value || "0", 10))
              }
              className="w-full px-4 py-3 border rounded-xl text-[15px] focus:outline-none focus:ring-2 focus:ring-orange-200 border-gray-200"
            />
          </Card>

          <Card className="p-4">
            <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
              <Users className="w-5 h-5 text-orange-500" />
              모집인원
            </label>
            <input
              type="number"
              value={formData.participants}
              min="1"
              onChange={(e) =>
                handleChange(
                  "participants",
                  parseInt(e.target.value || "1", 10)
                )
              }
              className="w-full px-4 py-3 border rounded-xl text-[15px] focus:outline-none focus:ring-2 focus:ring-orange-200 border-gray-200"
            />
          </Card>
        </div>

        {/* 작성자 */}
        <Card className="p-4">
          <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
            <User className="w-5 h-5 text-orange-500" />
            작성자 (선택)
          </label>
          <input
            type="text"
            value={formData.client}
            onChange={(e) => handleChange("client", e.target.value)}
            placeholder="예: 김OO"
            className="w-full px-4 py-3 border rounded-xl text-[15px] focus:outline-none focus:ring-2 focus:ring-orange-200 border-gray-200"
          />
        </Card>

        {/* 상세 설명 */}
        <Card className="p-4">
          <label className="text-sm font-semibold text-gray-700 mb-2 block">
            상세 설명
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => handleChange("description", e.target.value)}
            rows={6}
            placeholder="공고 상세 내용을 입력하세요."
            className="w-full px-4 py-3 border rounded-xl text-[15px] leading-relaxed focus:outline-none focus:ring-2 focus:ring-orange-200 border-gray-200 resize-none"
          />
        </Card>

        {/* 안내 박스 */}
        <Card className="p-4 border-blue-200">
          <p className="text-blue-700 text-sm">
            💡 <strong>안내:</strong> 작성하신 내용은 등록 후에도 수정할 수
            있어요.
          </p>
        </Card>
      </main>

      
    </div>
  );
}