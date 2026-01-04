// src/pages/jobs/JobPostedList.js
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, MoreVertical, Edit, Trash2, Users, Eye } from "lucide-react";

import {
  ApiError,
  JobsAPI,
  MyJobsAPI,
  parseApiError,
  toCurrency,
} from "../../utils/apiClient";

const fmtDate = (iso) => (iso ? iso.slice(0, 10).replaceAll("-", ".") : "");
const diffDays = (toIso) => {
  if (!toIso) return null;
  const target = new Date(toIso);
  const today = new Date();
  const ms = target.setHours(0, 0, 0, 0) - today.setHours(0, 0, 0, 0);
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)));
};

export default function JobPostedList() {
  const nav = useNavigate();
  const [showMenu, setShowMenu] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setErr("");
      try {
        const data = await MyJobsAPI.list();
        if (!mounted) return;
        const list = Array.isArray(data) ? data : data?.items || [];
        const normalized = list.map((job) => {
          const payValue = job.pay ?? job.hourly_wage ?? job.wage;
          return {
            id: job.id,
            title: job.title || "-",
            location: job.place || job.location || job.address || "",
            schedule: job.time || job.schedule || "",
            payText: job.pay_text || (payValue != null ? `시급 ${toCurrency(payValue)}` : "협의"),
            status: job.status === "open" ? "active" : "closed",
            statusText: job.status === "open" ? "모집중" : "마감",
            appliedCount: job.applicants_count ?? 0,
            viewCount: job.views ?? job.view_count ?? 0,
            postedDate: fmtDate(job.created_at),
            daysLeft: diffDays(job.deadline),
            raw: job,
          };
        });
        setJobs(normalized);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          setErr("로그인이 만료되었습니다. 다시 로그인해주세요.");
          setTimeout(() => nav("/login"), 600);
        } else {
          setErr(parseApiError(e));
        }
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [nav]);

  const handleBack = () => {
    if (window.history.length > 1) nav(-1);
    else nav("/matchingpage");
  };

  const handleJobClick = (jobId) => {
    nav(`/jobdetail/${jobId}`);
  };

  const handleEdit = (jobId, e) => {
    e.stopPropagation();
    setShowMenu(null);
    nav(`/jobdetail/${jobId}`); // TODO: replace with 실제 수정 경로
  };

  const handleDelete = async (jobId, e) => {
    e.stopPropagation();
    setShowMenu(null);
    if (!window.confirm("정말 삭제하시겠습니까?")) return;

    try {
      await JobsAPI.delete(jobId);
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
      alert("공고가 삭제되었습니다.");
    } catch (error) {
      alert(parseApiError(error, "삭제에 실패했어요. 잠시 후 다시 시도해 주세요."));
    }
  };

  const toggleMenu = (jobId, e) => {
    e.stopPropagation();
    setShowMenu((prev) => (prev === jobId ? null : jobId));
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      <header className="bg-white px-6 py-5 border-b sticky top-0 z-10">
        <div className="flex items-center">
          <button onClick={handleBack} className="p-2 -ml-2" aria-label="뒤로가기">
            <ChevronLeft className="w-7 h-7" />
          </button>
          <h1 className="text-2xl font-bold text-gray-800 ml-2">내가 올린 공고</h1>
        </div>
      </header>

      <main className="px-6 py-6">
        {err && (
          <div className="mb-4 p-3 rounded-xl bg-rose-50 text-rose-700 text-sm">
            {err}
          </div>
        )}

        {loading ? (
          <SkeletonList />
        ) : jobs.length > 0 ? (
          <div className="space-y-4">
            {jobs.map((job) => (
              <div
                key={job.id}
                onClick={() => handleJobClick(job.id)}
                className="bg-white rounded-2xl p-6 shadow-md hover:shadow-lg transition cursor-pointer relative"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-bold ${
                          job.status === "active"
                            ? "bg-green-100 text-green-600"
                            : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {job.statusText}
                      </span>
                      {job.daysLeft != null && (
                        <span className="text-sm text-gray-500">
                          마감 {job.daysLeft}일 전
                        </span>
                      )}
                    </div>
                    <h3 className="text-xl font-bold text-gray-800">{job.title}</h3>
                    <p className="text-gray-600 text-sm mt-2">{job.location}</p>
                    <p className="text-gray-600 text-sm">{job.schedule}</p>
                    <p className="text-gray-900 font-semibold text-lg mt-2">{job.payText}</p>
                  </div>

                  <div className="relative">
                    <button
                      onClick={(e) => toggleMenu(job.id, e)}
                      className="p-2 hover:bg-gray-100 rounded-lg"
                      aria-haspopup="menu"
                      aria-expanded={showMenu === job.id}
                      aria-label="메뉴 열기"
                    >
                      <MoreVertical className="w-5 h-5 text-gray-500" />
                    </button>
                    {showMenu === job.id && (
                      <div className="absolute right-0 mt-2 w-40 bg-white border rounded-xl shadow-lg z-20">
                        <button
                          onClick={(e) => handleEdit(job.id, e)}
                          className="w-full px-4 py-3 text-left text-sm hover:bg-gray-100 flex items-center gap-2"
                        >
                          <Edit className="w-4 h-4" /> 수정하기
                        </button>
                        <button
                          onClick={(e) => handleDelete(job.id, e)}
                          className="w-full px-4 py-3 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                        >
                          <Trash2 className="w-4 h-4" /> 삭제하기
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-4 text-sm text-gray-500">
                  <span className="flex items-center gap-1">
                    <Users className="w-4 h-4" /> 지원자 {job.appliedCount}명
                  </span>
                  <span className="flex items-center gap-1">
                    <Eye className="w-4 h-4" /> 조회수 {job.viewCount}
                  </span>
                  {job.postedDate && <span>등록일 {job.postedDate}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState />
        )}
      </main>
    </div>
  );
}

function SkeletonList() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-40 rounded-2xl bg-gray-200 animate-pulse" />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-20">
      <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <span className="text-4xl">🗂️</span>
      </div>
      <p className="text-gray-500 text-lg">등록한 공고가 없습니다</p>
    </div>
  );
}
