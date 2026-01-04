//공고 등록 하는 페이지인데 현재 음성/이미지 업로드 확인이 안돼서 진행 불가
import React, { useEffect, useMemo, useState } from "react";
import { ChevronLeft, Edit, Upload as UploadIcon } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  JobsAPI,
  parseApiError,
  getStoredToken,
} from "../../../utils/apiClient";

// mapped_fields 예시 키: title, category, location, schedule, time, duration, wage/pay, requirements, description
export default function JobPost() {
  const nav = useNavigate();
  const { state } = useLocation() || {};
  const init = useMemo(() => {
    const mf = state?.mapped_fields || {};
    const rawText = (state?.raw_text || "").trim();
    return {
      title: mf.title || "반려동물 산책 도우미",
      category: mf.category || "생활 보조",
      location: mf.location || "서울 성동구 행당동",
      schedule: mf.schedule || "주 5회 (월~금)",
      time: mf.time || "오전 9시, 오후 6시 (1일 2회)",
      duration: mf.duration || "1회당 30분",
      pay: mf.wage || mf.pay || "시급 15,000원",
      requirements: mf.requirements || "",
      description: mf.description || rawText || "",
    };
  }, [state]);

  const [formData, setFormData] = useState(init);
  const [isEditing, setIsEditing] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => { setFormData(init); }, [init]);

  const handleChange = (field, value) => {
    setErrMsg("");
    setFormData((p) => ({ ...p, [field]: value }));
  };

  const handleBack = () => {
    if (window.history.length > 1) nav(-1);
    else nav("/");
  };

  const validate = () => {
    if (!formData.title?.trim()) return "공고 제목을 입력해주세요.";
    if (!formData.location?.trim()) return "근무 지역을 입력해주세요.";
    if (!formData.pay?.toString().trim()) return "급여를 입력해주세요.";
    if (!formData.description?.trim()) return "상세 설명을 입력해주세요.";
    return "";
  };

  const normalizeForApi = () => {
    // 문자열 파싱이 필요하면 여기서 정규화(숫자 추출 등)
    return {
      title: formData.title.trim(),
      category: formData.category?.trim() || null,
      location: formData.location.trim(),
      schedule: formData.schedule?.trim() || null,
      time: formData.time?.trim() || null,
      duration: formData.duration?.trim() || null,
      wage: formData.pay?.toString().trim(),
      requirements: formData.requirements?.trim() || null,
      description: formData.description.trim(),
    };
  };

  const handleSubmit = async () => {
    setErrMsg("");
    const v = validate();
    if (v) { setErrMsg(v); return; }
    const token = getStoredToken();
    if (!token) { setErrMsg("로그인이 필요합니다. 먼저 로그인해주세요."); return; }

    const fields = normalizeForApi();

    setLoading(true);
    try {
      // 계약표에 맞춘 최종 생성 API
      const data = await JobsAPI.createFromAi(fields);

      // 상세로 이동(백엔드에 따라 폴링/상태 대기 대신 상세페이지 진입)
      if (data?.job_id) nav(`/jobs/${data.job_id}`, { replace: true });
      else nav("/jobs", { replace: true });
    } catch (e) {
      setErrMsg(parseApiError(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col pb-24">
      <header className="px-6 py-4 flex items-center justify-between border-b sticky top-0 bg-white z-10">
        <div className="flex items-center">
          <button onClick={handleBack} className="p-2"><ChevronLeft className="w-6 h-6" /></button>
          <h1 className="text-lg font-bold ml-4">공고 확인</h1>
        </div>
        <button
          onClick={() => setIsEditing(v => !v)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-gray-100"
        >
          <Edit className="w-5 h-5 text-[#F4BA4D]" />
          <span className="font-medium text-[#F4BA4D]">{isEditing ? "완료" : "수정"}</span>
        </button>
      </header>

      <main className="flex-1 px-6 py-6">
        {errMsg && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 mb-4 whitespace-pre-line">
            {errMsg}
          </div>
        )}
        <div className="bg-[#FEF3E2] rounded-xl p-4 mb-6">
          <p className="text-[#F4BA4D] font-medium text-center">✨ AI가 자동으로 작성한 공고입니다</p>
        </div>

        <div className="space-y-6">
          {[
            ["title","공고 제목","input"],
            ["category","카테고리","input"],
            ["location","근무 지역","input"],
            ["schedule","근무 일정","input"],
            ["time","근무 시간","input"],
            ["duration","소요 시간","input"],
            ["pay","급여","input"],
          ].map(([key,label,type])=>(
            <div key={key}>
              <label className="block text-sm font-bold text-gray-700 mb-2">{label}</label>
              {isEditing ? (
                <input
                  type="text"
                  value={formData[key] ?? ""}
                  onChange={(e)=>handleChange(key, e.target.value)}
                  className="w-full px-4 py-3 border-2 border-[#F4BA4D] rounded-xl text-lg focus:outline-none"
                />
              ) : (
                key==="pay"
                  ? <div className="bg-[#FEF3E2] px-4 py-3 rounded-lg inline-block">
                      <p className="text-xl font-bold text-[#F4BA4D]">{formData[key]}</p>
                    </div>
                  : <p className="text-lg">{formData[key]}</p>
              )}
            </div>
          ))}

          {/* 지원 자격 */}
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">지원 자격</label>
            {isEditing ? (
              <textarea
                value={formData.requirements ?? ""}
                onChange={(e) => handleChange("requirements", e.target.value)}
                rows={3}
                className="w-full px-4 py-3 border-2 border-[#F4BA4D] rounded-xl text-lg focus:outline-none resize-none"
              />
            ) : (
              <p className="text-lg whitespace-pre-line">{formData.requirements}</p>
            )}
          </div>

          {/* 상세 설명 */}
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">상세 설명</label>
            {isEditing ? (
              <textarea
                value={formData.description ?? ""}
                onChange={(e) => handleChange("description", e.target.value)}
                rows={4}
                className="w-full px-4 py-3 border-2 border-[#F4BA4D] rounded-xl text-lg focus:outline-none resize-none"
              />
            ) : (
              <p className="text-lg whitespace-pre-line">{formData.description}</p>
            )}
          </div>
        </div>
      </main>

      <div className="fixed bottom-0 left-0 right-0 bg-white border-t px-6 py-4">
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full bg-[#F4BA4D] text-white font-bold text-xl py-5 rounded-xl hover:bg-[#E5AB3D] transition flex items-center justify-center gap-2 disabled:opacity-60"
        >
          <UploadIcon className="w-6 h-6" />
          <span>{loading ? "등록 중..." : "공고 등록하기"}</span>
        </button>
      </div>
    </div>
  );
}
