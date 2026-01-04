// src/pages/applications/JobApplicationList.js
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, Calendar, MapPin, Clock, DollarSign } from "lucide-react";

import {
  ApiError,
  ApplicationsAPI,
  parseApiError,
  toCurrency,
} from "../../utils/apiClient";

const fmtDate = (iso) => (iso ? iso.slice(0, 10).replaceAll("-", ".") : "");

export default function JobApplicationList() {
  const nav = useNavigate();
  const [filter, setFilter] = useState("all");
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setErr("");
      try {
        const data = await ApplicationsAPI.list({ me: "sent" });
        if (!mounted) return;
        const list = Array.isArray(data) ? data : data?.items || [];
        setApplications(list);
      } catch (e) {
        if (!mounted) return;
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

  const filteredApplications = useMemo(() => {
    if (filter === "all") return applications;
    return applications.filter((a) => a.status === filter);
  }, [applications, filter]);

  const counts = useMemo(
    () => ({
      all: applications.length,
      pending: applications.filter((a) => a.status === "pending").length,
      approved: applications.filter((a) => a.status === "approved").length,
      rejected: applications.filter((a) => a.status === "rejected").length,
    }),
    [applications]
  );

  const getStatusColor = (status) => {
    switch (status) {
      case "approved":
        return "bg-green-100 text-green-700 border-green-200";
      case "pending":
        return "bg-yellow-100 text-yellow-700 border-yellow-200";
      case "rejected":
        return "bg-red-100 text-red-600 border-red-200";
      default:
        return "bg-gray-100 text-gray-600 border-gray-200";
    }
  };

  const statusText = (status, fallback) => {
    if (fallback) return fallback;
    switch (status) {
      case "approved":
        return "승인됨";
      case "pending":
        return "검토중";
      case "rejected":
        return "거절됨";
      default:
        return "확인중";
    }
  };

  const handleBack = () => {
    if (window.history.length > 1) nav(-1);
    else nav("/matchingpage");
  };

  const handleJobClick = (app) => {
    const jobId = app?.job?.id || app?.job_id || app?.job?.job_id || app?.id;
    if (jobId) nav(`/jobdetail/${jobId}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      <header className="bg-white px-6 py-5 border-b sticky top-0 z-10">
        <div className="flex items-center mb-4">
          <button onClick={handleBack} className="p-2 -ml-2" aria-label="뒤로가기">
            <ChevronLeft className="w-7 h-7" />
          </button>
          <h1 className="text-2xl font-bold text-gray-800 ml-2">지원 내역</h1>
        </div>

        <div className="flex gap-2 overflow-x-auto">
          <TabBtn onClick={() => setFilter("all")} active={filter === "all"}>
            전체 ({counts.all})
          </TabBtn>
          <TabBtn onClick={() => setFilter("pending")} active={filter === "pending"}>
            검토중 ({counts.pending})
          </TabBtn>
          <TabBtn onClick={() => setFilter("approved")} active={filter === "approved"}>
            승인됨 ({counts.approved})
          </TabBtn>
          <TabBtn onClick={() => setFilter("rejected")} active={filter === "rejected"}>
            거절됨 ({counts.rejected})
          </TabBtn>
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
        ) : filteredApplications.length > 0 ? (
          <div className="space-y-4">
            {filteredApplications.map((app) => {
              const job = app.job || {};
              const location = job.place || job.location || job.address || app.location || "";
              const schedule = job.schedule || job.time || app.schedule || "";
              const payValue = job.pay ?? job.hourly_wage ?? job.wage;
              const payText = job.pay_text || app.pay || (payValue != null ? `시급 ${toCurrency(payValue)}` : "협의");
              const appliedAt = app.applied_at || app.appliedDate;

              return (
                <div
                  key={app.id}
                  onClick={() => handleJobClick(app)}
                  className="bg-white rounded-2xl p-6 shadow-md hover:shadow-lg transition cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-4">
                    <h3 className="text-xl font-bold text-gray-800 flex-1 pr-3">
                      {job.title || app.title || "-"}
                    </h3>
                    <span
                      className={`px-4 py-2 rounded-xl text-base font-bold border-2 whitespace-nowrap ${getStatusColor(
                        app.status
                      )}`}
                    >
                      {statusText(app.status, app.statusText)}
                    </span>
                  </div>

                  {job.company || app.company ? (
                    <p className="text-gray-500 text-base mb-4 font-medium">
                      {job.company || app.company}
                    </p>
                  ) : null}

                  <div className="space-y-3 mb-4">
                    <InfoRow icon={<MapPin className="w-5 h-5 text-[#F4BA4D]" />}>{location}</InfoRow>
                    <InfoRow icon={<Clock className="w-5 h-5 text-[#F4BA4D]" />}>{schedule}</InfoRow>
                    <InfoRow icon={<DollarSign className="w-5 h-5 text-[#F4BA4D]" />}>{payText}</InfoRow>
                  </div>

                  {appliedAt && (
                    <div className="pt-4 border-t border-gray-200">
                      <div className="flex items-center gap-2 text-gray-500 text-sm">
                        <Calendar className="w-4 h-4" />
                        <span>지원일: {fmtDate(appliedAt)}</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState />
        )}
      </main>
    </div>
  );
}

function TabBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-5 py-2 rounded-xl font-bold text-base whitespace-nowrap transition ${
        active ? "bg-[#F4BA4D] text-white" : "bg-gray-100 text-gray-600"
      }`}
    >
      {children}
    </button>
  );
}

function SkeletonList() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-36 rounded-2xl bg-gray-200 animate-pulse" />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-20">
      <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <span className="text-4xl">📋</span>
      </div>
      <p className="text-gray-500 text-lg">해당하는 지원 내역이 없습니다</p>
    </div>
  );
}

function InfoRow({ icon, children }) {
  return (
    <div className="flex items-center gap-3">
      {icon}
      <span className="text-gray-700 text-base">{children}</span>
    </div>
  );
}
