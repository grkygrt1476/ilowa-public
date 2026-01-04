import React, { useState, useEffect, useCallback } from "react";

const BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:8000";

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("admin_access_token") || "";
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path.startsWith("http") ? path : `${BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${text}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : null;
}

export default function AdminApproval() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [filter, setFilter] = useState("pending");
  const [selectedJob, setSelectedJob] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      setErr("");
      const data = await apiFetch(`/api/v1/admin/jobs?status=${filter}`);
      setJobs(data?.jobs || data || []);
    } catch (e) {
      setErr("공고 목록을 불러오는데 실패했습니다.");
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleAction = async (jobId, action) => {
    if (!window.confirm(`이 공고를 ${action === "approve" ? "승인" : "거절"}하시겠습니까?`)) return;
    
    try {
      setActionLoading(true);
      await apiFetch(`/api/v1/admin/jobs/${jobId}/${action}`, {
        method: "POST",
      });
      alert(`공고가 ${action === "approve" ? "승인" : "거절"}되었습니다.`);
      setSelectedJob(null);
      fetchJobs();
    } catch (e) {
      alert("처리 중 오류가 발생했습니다.");
      console.error(e);
    } finally {
      setActionLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("admin_access_token");
    window.location.href = "/admin/login";
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: "bg-yellow-100 text-yellow-800",
      approved: "bg-green-100 text-green-800",
      rejected: "bg-red-100 text-red-800",
    };
    const labels = {
      pending: "대기중",
      approved: "승인됨",
      rejected: "거절됨",
    };
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${badges[status] || "bg-gray-100 text-gray-800"}`}>
        {labels[status] || status}
      </span>
    );
  };

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleDateString("ko-KR", { 
      year: "numeric", 
      month: "2-digit", 
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">관리자 대시보드</h1>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-600 hover:text-gray-900 underline"
          >
            로그아웃
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="bg-white rounded-2xl shadow-md p-6 mb-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">공고 승인 관리</h2>
          <div className="flex gap-2 flex-wrap">
            {[
              { value: "pending", label: "대기중" },
              { value: "approved", label: "승인됨" },
              { value: "rejected", label: "거절됨" },
              { value: "all", label: "전체" },
            ].map((tab) => (
              <button
                key={tab.value}
                onClick={() => setFilter(tab.value)}
                className={`px-4 py-2 rounded-xl font-semibold transition-colors ${
                  filter === tab.value
                    ? "bg-orange-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {err && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 text-rose-700">
            {err}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-orange-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600">공고를 불러오는 중...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-md p-12 text-center">
            <p className="text-gray-500">표시할 공고가 없습니다.</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="bg-white rounded-2xl shadow-md p-6 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-bold text-gray-900">{job.title}</h3>
                      {getStatusBadge(job.status)}
                    </div>
                    <p className="text-gray-600 mb-2">{job.company_name}</p>
                    <p className="text-sm text-gray-500">
                      등록일: {formatDate(job.created_at)}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                  <div>
                    <span className="text-gray-500">근무지:</span>
                    <span className="ml-2 text-gray-900">{job.location || "-"}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">급여:</span>
                    <span className="ml-2 text-gray-900">{job.salary || "-"}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">근무시간:</span>
                    <span className="ml-2 text-gray-900">{job.work_hours || "-"}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">모집인원:</span>
                    <span className="ml-2 text-gray-900">{job.positions || "-"}명</span>
                  </div>
                </div>

                {job.description && (
                  <p className="text-gray-700 text-sm mb-4 line-clamp-2">
                    {job.description}
                  </p>
                )}

                <div className="flex gap-2 pt-4 border-t">
                  <button
                    onClick={() => setSelectedJob(job)}
                    className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-2 rounded-xl transition-colors"
                  >
                    상세보기
                  </button>
                  {job.status === "pending" && (
                    <>
                      <button
                        onClick={() => handleAction(job.id, "approve")}
                        disabled={actionLoading}
                        className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-2 rounded-xl disabled:opacity-50 transition-colors"
                      >
                        승인
                      </button>
                      <button
                        onClick={() => handleAction(job.id, "reject")}
                        disabled={actionLoading}
                        className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold py-2 rounded-xl disabled:opacity-50 transition-colors"
                      >
                        거절
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedJob && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-6 z-50">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">{selectedJob.title}</h2>
                {getStatusBadge(selectedJob.status)}
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">회사명</h3>
                <p className="text-gray-700">{selectedJob.company_name}</p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">근무지</h3>
                <p className="text-gray-700">{selectedJob.location || "-"}</p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">급여</h3>
                <p className="text-gray-700">{selectedJob.salary || "-"}</p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">근무시간</h3>
                <p className="text-gray-700">{selectedJob.work_hours || "-"}</p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">모집인원</h3>
                <p className="text-gray-700">{selectedJob.positions || "-"}명</p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">상세설명</h3>
                <p className="text-gray-700 whitespace-pre-wrap">{selectedJob.description || "-"}</p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">등록일시</h3>
                <p className="text-gray-700">{formatDate(selectedJob.created_at)}</p>
              </div>
              {selectedJob.updated_at && (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">수정일시</h3>
                  <p className="text-gray-700">{formatDate(selectedJob.updated_at)}</p>
                </div>
              )}
            </div>

            {selectedJob.status === "pending" && (
              <div className="flex gap-2 mt-6 pt-6 border-t">
                <button
                  onClick={() => handleAction(selectedJob.id, "approve")}
                  disabled={actionLoading}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-xl disabled:opacity-50"
                >
                  승인하기
                </button>
                <button
                  onClick={() => handleAction(selectedJob.id, "reject")}
                  disabled={actionLoading}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold py-3 rounded-xl disabled:opacity-50"
                >
                  거절하기
                </button>
              </div>
            )}

            <button
              onClick={() => setSelectedJob(null)}
              className="w-full mt-3 bg-gray-100 text-gray-700 font-semibold py-3 rounded-xl hover:bg-gray-200"
            >
              닫기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
