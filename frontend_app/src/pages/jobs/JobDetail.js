// src/pages/jobs/JobDetailOwner.js
import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ChevronLeft, Edit, Trash2, Users, Eye, MapPin, Calendar, Clock, DollarSign
} from "lucide-react";

import {
  ApiError,
  JobsAPI,
  UsersAPI,
  ApplicationsAPI,
  parseApiError,
  toCurrency,
} from "../../utils/apiClient";

/** 유틸 */
const fmtDate = (iso) => (iso ? iso.slice(0, 10).replaceAll("-", ".") : "");
function daysUntil(iso) {
  if (!iso) return 0;
  const end = new Date(iso), today = new Date();
  const ms = end.setHours(0,0,0,0) - today.setHours(0,0,0,0);
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)));
}

export default function JobDetailOwner() {
  const { id } = useParams();               // ✅ /job/:id
  const nav = useNavigate();

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [job, setJob] = useState(null);
  const [applicants, setApplicants] = useState([]);
  const [isOwner, setIsOwner] = useState(false);
  const [applyNote, setApplyNote] = useState("잘 부탁드립니다.");
  const [applyFeedback, setApplyFeedback] = useState("");
  const [applying, setApplying] = useState(false);

  // ✅ 데이터 로드
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true); setErr("");
        const [jobRes, meRes] = await Promise.all([
          JobsAPI.detail(id),
          UsersAPI.me().catch(() => null),
        ]);

        if (!mounted) return;
        const ownerMatch =
          !!meRes &&
          jobRes?.owner_id &&
          meRes?.user_id &&
          String(jobRes.owner_id) === String(meRes.user_id);

        const normalizedJob = {
          id: jobRes?.id,
          ownerId: jobRes?.owner_id,
          title: jobRes?.title || "-",
          location: jobRes?.place || jobRes?.location || "-",
          schedule: jobRes?.schedule || jobRes?.time || "-",
          time: jobRes?.time || "-",
          duration: jobRes?.duration || "",
          pay: (() => {
            const payValue = jobRes?.pay ?? jobRes?.hourly_wage ?? jobRes?.wage;
            if (payValue != null) return `시급 ${toCurrency(payValue)}`;
            return jobRes?.pay_text || jobRes?.wage_text || "협의";
          })(),
          requirements: jobRes?.requirements || "",
          description: jobRes?.description || "",
          status: jobRes?.status === "open" ? "active" : "closed",
          postedDate: fmtDate(jobRes?.created_at),
          daysLeft: daysUntil(jobRes?.deadline),
          appliedCount: jobRes?.applicants_count ?? 0,
          viewCount: jobRes?.views ?? jobRes?.view_count ?? 0,
          imageUrls: Array.isArray(jobRes?.images) ? jobRes.images : [],
        };
        let normalizedApps = [];
        if (ownerMatch) {
          try {
            const appsRes = await JobsAPI.applicants(id);
            normalizedApps = (Array.isArray(appsRes) ? appsRes : appsRes?.items || []).map(a => ({
              id: a.id,
              name: a.name || a.nickname || "지원자",
              age: a.age ?? "",
              region: a.region || a.address_area || "",
              experience: a.experience || a.bio || "",
              appliedDate: fmtDate(a.applied_at),
            }));
          } catch (appsErr) {
            if (!(appsErr instanceof ApiError && appsErr.status === 403)) {
              throw appsErr;
            }
          }
        }

        setJob(normalizedJob);
        setApplicants(normalizedApps);
        setIsOwner(ownerMatch);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          setErr("로그인이 만료되었습니다. 다시 로그인해주세요.");
          setTimeout(() => window.location.assign("/login"), 800);
        } else {
          setErr(parseApiError(e));
        }
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [id]);

  // ✅ 네비게이션/액션
  const handleBack = () => (window.history.length > 1 ? nav(-1) : nav("/my-jobs"));
  const handleEdit = () => nav(`/job/${id}/edit`);     // ✅ 수정 페이지로 이동
  const handleConfirm = () => nav("/main");
  const handleDelete = async () => {
    try {
      if (!window.confirm("정말 삭제하시겠습니까?")) return;  // ESLint OK
      await JobsAPI.delete(id);
      setShowDeleteModal(false);
      alert("공고가 삭제되었습니다.");
      nav("/my-jobs");
    } catch (error) {
      alert(parseApiError(error));
    }
  };
  const handleApplicantClick = (appId) => {
    // nav(`/job/${id}/applicants/${appId}`);
    alert(`지원자 상세 페이지로 이동합니다. ID: ${appId}`);
  };

  const handleApplySubmit = async () => {
    if (!job) return;
    setApplying(true);
    setApplyFeedback("");
    try {
      await ApplicationsAPI.apply({ job_id: job.id, note: applyNote });
      setApplyFeedback("지원이 완료되었습니다. 승인 결과는 알림함에서 확인해주세요.");
    } catch (error) {
      setApplyFeedback(parseApiError(error, "지원에 실패했어요. 다시 시도해주세요."));
    } finally {
      setApplying(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <header className="bg-white px-6 py-5 border rounded-2xl mb-4">
          <div className="h-6 w-32 bg-gray-200 rounded animate-pulse" />
        </header>
        <div className="h-48 bg-gray-200 rounded-2xl animate-pulse mb-4" />
        <div className="h-72 bg-gray-200 rounded-2xl animate-pulse" />
      </div>
    );
  }
  if (err) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <button onClick={handleBack} className="mb-4 px-3 py-2 bg-white border rounded-xl">
          뒤로가기
        </button>
        <div className="p-4 bg-rose-50 text-rose-700 rounded-xl">{err}</div>
      </div>
    );
  }
  if (!job) return null;

  return (
    <div className="min-h-screen bg-gray-50 pb-32">
      {/* 헤더 */}
      <header className="bg-white px-6 py-5 border-b sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <button onClick={handleBack} className="p-2 -ml-2" aria-label="뒤로가기">
            <ChevronLeft className="w-7 h-7" />
          </button>
          <div className="flex gap-2">
            {isOwner ? (
              <>
                <button onClick={handleConfirm} className="flex items-center gap-2 px-4 py-2 bg-green-50 text-green-600 rounded-xl hover:bg-green-500 hover:text-white transition">
                  <span className="font-bold">확인</span>
                </button>
                <button onClick={handleEdit} className="flex items-center gap-2 px-4 py-2 bg-[#FEF3E2] rounded-xl hover:bg-[#F4BA4D] hover:text-white transition">
                  <Edit className="w-5 h-5" />
                  <span className="font-bold">수정</span>
                </button>
                <button onClick={() => setShowDeleteModal(true)} className="flex items-center gap-2 px-4 py-2 bg-red-50 rounded-xl hover:bg-red-500 hover:text-white transition">
                  <Trash2 className="w-5 h-5" />
                  <span className="font-bold">삭제</span>
                </button>
              </>
            ) : (
              <button
                onClick={() =>
                  document
                    .getElementById("apply-section")
                    ?.scrollIntoView({ behavior: "smooth" })
                }
                className="px-5 py-2 rounded-xl bg-orange-500 text-white font-bold hover:bg-orange-600 transition"
              >
                지원하기
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="px-6 py-6">
        {/* 제목/상태 */}
        <div className="bg-white rounded-2xl p-6 mb-4 shadow-md">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">{job.title}</h1>
          <span className={`px-3 py-1 rounded-full text-sm font-bold ${job.status === "active" ? "bg-green-100 text-green-600" : "bg-gray-100 text-gray-600"}`}>
            {job.status === "active" ? "모집중" : "마감"}
          </span>
        </div>

        {/* 급여 */}
        <div className="bg-gradient-to-br from-[#FEF3E2] to-[#FFF8E7] rounded-2xl p-6 mb-4 shadow-md border-2 border-[#F4BA4D]">
          <div className="flex items-center gap-3 mb-2"><DollarSign className="w-7 h-7 text-[#F4BA4D]" /><span className="text-gray-700 font-bold text-lg">급여</span></div>
          <p className="text-3xl font-bold text-[#F4BA4D]">{job.pay}</p>
        </div>

        {/* 근무 정보 */}
        <div className="bg-white rounded-2xl p-6 mb-4 shadow-md space-y-4">
          <h3 className="text-lg font-bold text-gray-800 mb-4">📋 근무 정보</h3>
          <div className="flex items-start gap-3"><MapPin className="w-6 h-6 text-[#F4BA4D] mt-1" /><div><p className="text-gray-500 text-sm mb-1">근무 지역</p><p className="text-gray-800 text-lg font-medium">{job.location}</p></div></div>
          <div className="border-t border-gray-200" />
          <div className="flex items-start gap-3"><Calendar className="w-6 h-6 text-[#F4BA4D] mt-1" /><div><p className="text-gray-500 text-sm mb-1">근무 일정</p><p className="text-gray-800 text-lg font-medium">{job.schedule}</p></div></div>
          <div className="border-t border-gray-200" />
          <div className="flex items-start gap-3"><Clock className="w-6 h-6 text-[#F4BA4D] mt-1" /><div><p className="text-gray-500 text-sm mb-1">근무 시간</p><p className="text-gray-800 text-lg font-medium">{job.time}</p>{job.duration && <p className="text-gray-600 text-base mt-1">{job.duration}</p>}</div></div>
        </div>

        {/* 지원 자격 */}
        {job.requirements && (
          <div className="bg-white rounded-2xl p-6 mb-4 shadow-md">
            <h3 className="text-lg font-bold text-gray-800 mb-4">✅ 지원 자격</h3>
            <p className="text-gray-700 text-lg whitespace-pre-line leading-relaxed">{job.requirements}</p>
          </div>
        )}

        {/* 상세 설명 */}
        {job.description && (
          <div className="bg-white rounded-2xl p-6 mb-6 shadow-md">
            <h3 className="text-lg font-bold text-gray-800 mb-4">📄 상세 설명</h3>
            <p className="text-gray-700 text-lg whitespace-pre-line leading-relaxed">{job.description}</p>
          </div>
        )}

        {!isOwner && (
          <div id="apply-section" className="bg-white rounded-2xl p-6 mb-6 shadow-md">
            <h3 className="text-lg font-bold text-gray-800 mb-3">지금 바로 지원하기</h3>
            <p className="text-sm text-gray-600 mb-2">
              한 줄 메시지를 남기면 공고 작성자가 확인해요.
            </p>
            <textarea
              className="w-full rounded-2xl border border-gray-200 p-4 text-sm text-gray-800"
              rows={4}
              value={applyNote}
              onChange={(e) => setApplyNote(e.target.value)}
              maxLength={200}
            />
            {applyFeedback && (
              <p
                className={`mt-3 text-sm ${
                  applyFeedback.includes("완료")
                    ? "text-emerald-600"
                    : "text-rose-600"
                }`}
              >
                {applyFeedback}
              </p>
            )}
            <button
              onClick={handleApplySubmit}
              disabled={applying}
              className="w-full mt-4 bg-orange-500 hover:bg-orange-600 text-white font-semibold py-3 rounded-xl disabled:opacity-60 transition"
            >
              {applying ? "지원 중..." : "지원하기"}
            </button>
          </div>
        )}

        {isOwner && (
          <div className="bg-white rounded-2xl p-6 shadow-md">
            <h3 className="text-lg font-bold text-gray-800 mb-4">👥 지원자 목록 ({applicants.length}명)</h3>
            {applicants.length ? (
              <div className="space-y-3">
                {applicants.map((a) => (
                  <div key={a.id} onClick={() => handleApplicantClick(a.id)} className="bg-gray-50 rounded-xl p-4 hover:bg-gray-100 transition cursor-pointer">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-lg font-bold text-gray-800">{a.name} {a.age ? `(${a.age}세)` : ""}</h4>
                      {a.appliedDate && <span className="text-sm text-gray-500">{a.appliedDate}</span>}
                    </div>
                    {a.region && <p className="text-gray-600 text-base mb-1">📍 {a.region}</p>}
                    {a.experience && <p className="text-gray-600 text-base">💼 {a.experience}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-500">아직 지원자가 없습니다.</div>
            )}
          </div>
        )}

        {/* 통계 - 페이지 하단 */}
        <div className="bg-gradient-to-r from-[#F4BA4D] to-[#E5AB3D] rounded-2xl p-6 mt-6 shadow-lg">
          <h3 className="text-white font-bold text-lg mb-4">📊 공고 현황</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white bg-opacity-20 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2"><Users className="w-5 h-5 text-white" /><span className="text-white text-sm">지원자</span></div>
              <p className="text-white text-3xl font-bold">{job.appliedCount}명</p>
            </div>
            <div className="bg-white bg-opacity-20 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2"><Eye className="w-5 h-5 text-white" /><span className="text-white text-sm">조회수</span></div>
              <p className="text-white text-3xl font-bold">{job.viewCount}</p>
            </div>
          </div>
          {job.daysLeft != null && (
            <div className="mt-4 pt-4 border-t border-white/30">
              <p className="text-white text-base">마감까지 <span className="font-bold text-xl">{job.daysLeft}일</span> 남음</p>
            </div>
          )}
        </div>
      </main>

      {/* 삭제 확인 모달 */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-6">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full">
            <h3 className="text-xl font-bold text-gray-800 mb-3">공고를 삭제하시겠습니까?</h3>
            <p className="text-gray-600 text-base mb-6">삭제한 공고는 복구할 수 없습니다.</p>
            <div className="flex gap-3">
              <button onClick={() => setShowDeleteModal(false)} className="flex-1 bg-gray-200 text-gray-700 font-bold py-4 rounded-xl hover:bg-gray-300 transition">취소</button>
              <button onClick={handleDelete} className="flex-1 bg-red-500 text-white font-bold py-4 rounded-xl hover:bg-red-600 transition">삭제</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
