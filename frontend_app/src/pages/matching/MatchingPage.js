// src/pages/matching/MatchingPage.js
import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";

import { ApiError, apiFetch, parseApiError, toCurrency, UsersAPI, ApplicationsAPI } from "../../utils/apiClient";

export default function MatchingPage() {
  // all | applied | posted | matched
  const [mode, setMode] = useState("all");

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [seedReady, setSeedReady] = useState(false);

  // 지원하기 시트 대상
  const [applyTarget, setApplyTarget] = useState(null);
  const [manageTarget, setManageTarget] = useState(null);
  const [manageLoading, setManageLoading] = useState(false);
  const [manageErr, setManageErr] = useState("");
  const [manageApplicants, setManageApplicants] = useState([]);
  const [actioningId, setActioningId] = useState(null);
  const [cancelingId, setCancelingId] = useState(null);
  const [searchParams] = useSearchParams();
  const [pendingManageJob, setPendingManageJob] = useState(null);
  const [me, setMe] = useState(null);
  const [meLoading, setMeLoading] = useState(true);

  const nav = useNavigate();
  const handleBack = () => nav(-1);
  const handleSkip = () => nav("/"); // 필요 시 원하는 경로로 변경

  useEffect(() => {
    let active = true;
    UsersAPI.me()
      .then((data) => {
        if (active) setMe(data);
      })
      .catch(() => {
        if (active) setMe(null);
      })
      .finally(() => {
        if (active) setMeLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // CSV 기반 소일거리 데이터를 DB에 동기화
  useEffect(() => {
    let active = true;
    async function syncSeedData() {
      try {
        await apiFetch("/api/v1/jobs/seed-from-csv", {
          method: "POST",
          body: {},
        });
      } catch (e) {
        console.warn("[MatchingPage] seed sync skipped:", e);
      } finally {
        if (active) setSeedReady(true);
      }
    }
    syncSeedData();
    return () => {
      active = false;
    };
  }, []);

  // 데이터 로드
  useEffect(() => {
    if (!seedReady || meLoading) return;
    let mounted = true;

    async function load() {
      setLoading(true);
      setErr("");
      try {
        let data;

        if (mode === "all") {
          data = await apiFetch(`/api/v1/jobs?page=${page}`);
        } else if (mode === "applied") {
          data = await apiFetch(`/api/v1/applications?me=sent&page=${page}`);
        } else if (mode === "posted") {
          data = await apiFetch(`/api/v1/jobs/my/jobs?page=${page}`);
        } else {
          data = await apiFetch(`/api/v1/matches?me=all&page=${page}`);
        }

        if (!mounted) return;
        let list = Array.isArray(data) ? data : data?.items || [];
        if (mode === "applied" && me?.user_id) {
          list = list.filter(
            (app) => String(app.applicant_id) === String(me.user_id)
          );
        }
        setItems(list);
        setHasMore(Boolean(data?.has_more));
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
    }

    load();
    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, page, seedReady, meLoading]);

  // 모드 바뀌면 페이지 초기화
  useEffect(() => {
    setPage(1);
  }, [mode]);

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    const jobParam = searchParams.get("job");
    if (tabParam && ["all", "applied", "posted", "matched"].includes(tabParam)) {
      setMode(tabParam);
    }
    if (jobParam) {
      setPendingManageJob(jobParam);
      if (tabParam !== "posted") {
        setMode("posted");
      }
    }
  }, [searchParams]);

  useEffect(() => {
    if (!pendingManageJob || mode !== "posted" || items.length === 0) return;
    const target = items.find((it) => String(it.id) === String(pendingManageJob));
    if (target) {
      setManageTarget(target);
      setPendingManageJob(null);
    }
  }, [pendingManageJob, mode, items]);

  useEffect(() => {
    if (!manageTarget) return;
    let active = true;
    async function loadApplicants() {
      setManageLoading(true);
      setManageErr("");
      try {
        const data = await apiFetch(`/api/v1/jobs/${manageTarget.id}/applicants`);
        if (!active) return;
        const list = Array.isArray(data?.items) ? data.items : [];
        setManageApplicants(list);
      } catch (e) {
        if (!active) return;
        setManageErr(parseApiError(e, "지원자 정보를 불러오지 못했어요."));
      } finally {
        if (active) setManageLoading(false);
      }
    }
    loadApplicants();
    return () => {
      active = false;
    };
  }, [manageTarget]);

  const handleApplicantStatusChange = async (applicationId, nextStatus) => {
    if (!manageTarget) return;
    setActioningId(applicationId);
    try {
      const updated = await apiFetch(`/api/v1/applications/${applicationId}/status`, {
        method: "POST",
        body: { status: nextStatus },
      });
      setManageApplicants((prev) =>
        prev.map((app) => (app.id === applicationId ? { ...app, status: updated.status } : app))
      );
      alert(`지원 상태가 ${nextStatus === "approved" ? "승인" : "거절"}되었습니다.`);
    } catch (e) {
      alert(parseApiError(e, "상태 변경에 실패했습니다."));
    } finally {
      setActioningId(null);
    }
  };

  const handleCancelApplication = async (applicationId) => {
    if (!window.confirm("정말 이 지원을 취소할까요?")) return;
    setCancelingId(applicationId);
    try {
      await ApplicationsAPI.cancel(applicationId);
      setItems((prev) =>
        prev.map((app) =>
          app.id === applicationId ? { ...app, status: "cancelled" } : app
        )
      );
      alert("지원이 취소되었습니다.");
    } catch (e) {
      alert(parseApiError(e, "지원 취소에 실패했습니다."));
    } finally {
      setCancelingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* ✅ 너가 준 고정 상단바 */}
      <header className="fixed top-0 left-0 right-0 bg-white px-6 py-7 flex items-center justify-between border-b z-50">
        <button onClick={handleBack} className="p-2" type="button" aria-label="뒤로">
          <ChevronLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold">소일거리 매칭</h1>
        <button
          onClick={handleSkip}
          className="text-black-500 font-medium text-base"
          type="button"
        >
        
        </button>
      </header>

      {/* 헤더 오프셋 + 하단 네비 가림 방지 패딩 */}
      <div className="flex-1 flex flex-col mt-[92px] pb-[88px]">
        {/* 상단 2×2 카드 */}
        <div className="grid grid-cols-2 gap-3 p-4">
          <MenuCard
            label="전체 소일거리 조회"
            icon="🗂️"
            color="bg-orange-500"
            active={mode === "all"}
            value="all"
            onSelect={setMode}
          />
          <MenuCard
            label="지원 내역"
            icon="📄"
            color="bg-purple-500"
            active={mode === "applied"}
            value="applied"
            onSelect={setMode}
          />
          <MenuCard
            label="내가 올린 공고"
            icon="🧑‍💼"
            color="bg-teal-500"
            active={mode === "posted"}
            value="posted"
            onSelect={setMode}
          />
          <MenuCard
            label="매칭 내역 조회"
            icon="🤝"
            color="bg-amber-500"
            active={mode === "matched"}
            value="matched"
            onSelect={setMode}
          />
        </div>

        {/* 에러 배너 */}
        {err && <Banner type="error">{err}</Banner>}

        {/* 리스트 (스크롤 영역) */}
        <div className="flex-1 overflow-y-auto px-4 pb-4">
          {loading ? (
            <SkeletonList />
          ) : items.length === 0 ? (
            <EmptyState mode={mode} />
          ) : (
            <div className="space-y-3">
              {items.map((it) => {
                if (mode === "applied") {
                  return (
                    <AppliedCard
                      key={it.id}
                      app={it}
                      onContact={() =>
                        window.open(`tel:${it?.job?.contact || ""}`)
                      }
                      onCancel={() => handleCancelApplication(it.id)}
                      cancelling={cancelingId === it.id}
                    />
                  );
                }
                if (mode === "posted") {
                  return (
                    <MyPostCard
                      key={it.id}
                      job={it}
                      onToggleStatus={async () => {
                        try {
                          await apiFetch(`/api/v1/jobs/${it.id}`, {
                            method: "PATCH",
                            body: {
                              status:
                                it.status === "open" ? "closed" : "open",
                            },
                          });
                          // 낙관적 갱신
                          setItems((prev) =>
                            prev.map((j) =>
                              j.id === it.id
                                ? {
                                    ...j,
                                    status:
                                      j.status === "open" ? "closed" : "open",
                                  }
                                : j
                            )
                          );
                        } catch (_) {
                          alert("상태를 바꾸지 못했어요.");
                        }
                      }}
                      onManageApplicants={() => {
                    setManageTarget(it);
                      }}
                    />
                  );
                }
                if (mode === "matched") {
                  return <MatchCard key={it.id} m={it} />;
                }
                // mode === "all"
                return (
                  <JobCard
                    key={it.id}
                    job={it}
                    onDetail={() => {
                      // nav(`/jobs/${it.id}`);
                    }}
                    onApply={() => setApplyTarget(it)}
                  />
                );
              })}
            </div>
          )}

          {/* 페이지네이션 */}
          {hasMore && !loading && (
            <div className="flex justify-center mt-4">
              <button
                className="px-4 py-2 rounded-full bg-white border shadow-sm text-gray-700"
                onClick={() => setPage((p) => p + 1)}
              >
                더 보기
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 지원하기 바텀시트 (헤더/네비 위에 떠야 하므로 z-index 크게) */}
      {applyTarget && (
        <ApplySheet
          job={applyTarget}
          onClose={() => setApplyTarget(null)}
          onSubmitted={() => {
            setApplyTarget(null);
            // setMode("applied");
          }}
        />
      )}

      {manageTarget && (
        <ApplicantSheet
          job={manageTarget}
          applicants={manageApplicants}
          loading={manageLoading}
          error={manageErr}
          actioningId={actioningId}
          onChangeStatus={handleApplicantStatusChange}
          onClose={() => {
            setManageTarget(null);
            setManageApplicants([]);
            setManageErr("");
          }}
        />
      )}

    </div>
  );
}

/** ---------------------------
 *  Parts
 *  -------------------------- */
function MenuCard({ label, icon, color, active, onSelect, value }) {
  return (
    <button
      onClick={() => onSelect?.(value)}
      className={
        "flex flex-col justify-center items-center h-28 rounded-2xl shadow-sm transition-all " +
        (active ? `${color} text-white` : "bg-white text-gray-800 hover:shadow")
      }
      aria-pressed={active}
    >
      <span className="text-2xl mb-1" aria-hidden="true">
        {icon}
      </span>
      <span className="text-[16px] font-semibold">{label}</span>
    </button>
  );
}

function Banner({ type, children }) {
  const cls =
    type === "error"
      ? "bg-rose-50 text-rose-700"
      : "bg-amber-50 text-amber-800";
  return (
    <div className={`mx-4 mb-2 p-3 rounded-xl text-sm ${cls}`}>{children}</div>
  );
}

function SkeletonList() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-24 rounded-2xl bg-gray-200 animate-pulse" />
      ))}
    </div>
  );
}

function EmptyState({ mode }) {
  const msg =
    mode === "applied"
      ? "아직 지원 내역이 없어요. 전체 리스트에서 바로 지원해 보세요."
      : mode === "posted"
      ? "올린 공고가 없어요. 마이페이지에서 공고를 만들어 보세요."
      : mode === "matched"
      ? "매칭 내역이 아직 없어요. 관심 설정을 업데이트해 보세요."
      : "표시할 항목이 없어요. 잠시 후 다시 시도해 주세요.";
  return <div className="mt-8 text-center text-gray-500">{msg}</div>;
}

/** 공고 카드 (전체 리스트용) */
function JobCard({ job, onDetail, onApply }) {
  const payValue = job.pay ?? job.hourly_wage ?? job.wage;
  const payText = payValue != null ? toCurrency(payValue) : job.pay_text || job.wage_text || "협의";
  const place = job.place || job.location || job.address || job.region || "";
  const time = job.time || job.schedule || job.shift || "시간 미정";
  const ownerLabel =
    job.owner_name ||
    job.ownerName ||
    job.owner_id ||
    job.ownerId ||
    job.owner?.id ||
    job.raw?.owner_id ||
    job.raw?.ownerId ||
    "";
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-bold text-gray-900">{job.title}</h3>
          <p className="text-gray-600 text-sm mt-1">
            {time} · {place}
          </p>
          <p className="text-gray-700 text-sm mt-1">급여 {payText}</p>
          {ownerLabel ? (
            <p className="text-gray-500 text-xs mt-1">
              등록자:{" "}
              <span className="font-mono">
                {typeof ownerLabel === "string" && ownerLabel.length > 12
                  ? `${ownerLabel.slice(0, 8)}…`
                  : ownerLabel}
              </span>
            </p>
          ) : null}
        </div>
        <button
          className="text-sm text-gray-500 underline decoration-dotted"
          onClick={onDetail}
        >
          상세
        </button>
      </div>
      <div className="mt-3">
        <button
          onClick={onApply}
          className="w-full h-12 text-[18px] font-semibold rounded-xl bg-emerald-500 text-white shadow hover:bg-emerald-600"
        >
          지원하기
        </button>
      </div>
    </div>
  );
}

/** 지원 내역 카드 */
function AppliedCard({ app, onContact, onCancel, cancelling }) {
  const st = app.status; // pending | approved | rejected | cancelled
  const badge =
    st === "approved"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : st === "rejected"
      ? "bg-rose-50 text-rose-700 border-rose-200"
      : st === "cancelled"
      ? "bg-gray-100 text-gray-500 border-gray-200"
      : "bg-amber-50 text-amber-700 border-amber-200";
  const statusLabel =
    st === "approved"
      ? "승인됨"
      : st === "rejected"
      ? "거절됨"
      : st === "cancelled"
      ? "취소됨"
      : "승인 대기중";

  const payValue = app.job?.hourly_wage ?? app.job?.pay ?? app.job?.wage;
  const payText =
    payValue != null ? `시급 ${toCurrency(payValue)}` : app.job?.pay_text || "협의";
  const formatApplyDate = () => {
    if (!app.applied_at) return "-";
    return new Date(app.applied_at).toLocaleDateString("ko-KR", {
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
      <div className="flex justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-gray-900">
            {app.job?.title || app.title || "-"}
          </h3>
          <p className="text-gray-600 text-sm mt-1">
            {(app.job?.time || app.job?.schedule || "")} · {(app.job?.place || app.job?.location || "")}
          </p>
          <p className="text-gray-600 text-sm mt-1">급여 {payText}</p>
          <p className="text-xs text-gray-400 mt-1">지원일: {formatApplyDate()}</p>
        </div>
        <span
          className={`h-7 px-3 rounded-full border text-sm flex items-center ${badge}`}
        >
          {statusLabel}
        </span>
      </div>
      <p className="mt-2 text-sm text-gray-500">
        현재 상태: <span className="font-semibold text-gray-800">{statusLabel}</span>
      </p>
      <div className="mt-3 flex gap-2">
        {st === "approved" ? (
          <>
            <button
              onClick={onContact}
              className="flex-1 h-11 rounded-xl bg-blue-600 text-white font-semibold"
            >
              전화하기
            </button>
            <a
              href={`https://map.kakao.com/?q=${encodeURIComponent(
                app.job?.place || ""
              )}`}
              target="_blank"
              rel="noreferrer"
              className="flex-1 h-11 rounded-xl bg-gray-100 text-gray-800 font-semibold flex items-center justify-center"
            >
              길찾기
            </a>
          </>
        ) : st === "pending" ? (
          <>
            <button
              onClick={onCancel}
              disabled={cancelling}
              className="flex-1 h-11 rounded-xl bg-white border border-rose-200 text-rose-600 font-semibold disabled:opacity-60"
            >
              {cancelling ? "취소 중..." : "지원 취소"}
            </button>
            <button
              disabled
              className="flex-1 h-11 rounded-xl bg-gray-100 text-gray-400 font-semibold"
            >
              승인 대기중
            </button>
          </>
        ) : (
          <button
            disabled
            className="w-full h-11 rounded-xl bg-gray-100 text-gray-400 font-semibold"
          >
            {st === "rejected" ? "다른 공고를 확인해보세요" : "취소되었습니다"}
          </button>
        )}
      </div>
    </div>
  );
}

/** 내가 올린 공고 카드 */
function MyPostCard({ job, onToggleStatus, onManageApplicants }) {
  const place = job.place || job.location || job.address || "";
  const time = job.time || job.schedule || "";
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-bold text-gray-900">{job.title}</h3>
          <p className="text-gray-600 text-sm mt-1">
            {time} · {place}
          </p>
          <p className="text-gray-700 text-sm mt-1">
            상태:{" "}
            <b className="text-gray-900">
              {job.status === "open" ? "모집 중" : "마감"}
            </b>
          </p>
        </div>
        <span className="text-sm text-gray-500">
          지원자 {job.applicants_count ?? 0}명
        </span>
      </div>
      <div className="mt-3 flex gap-2">
        <button
          onClick={onToggleStatus}
          className="flex-1 h-11 rounded-xl bg-white border font-semibold"
        >
          {job.status === "open" ? "마감하기" : "모집 재개"}
        </button>
        <button
          onClick={onManageApplicants}
          className="flex-1 h-11 rounded-xl bg-emerald-500 text-white font-semibold"
        >
          지원자 관리
        </button>
      </div>
    </div>
  );
}

/** 매칭 내역 카드 (AI 추천/성사 기록) */
function MatchCard({ m }) {
  const place =
    m.job?.place || m.job?.location || m.job?.address || m.job?.region || m.place || "";
  const time = m.job?.time || m.job?.schedule || m.job?.shift || m.time || "시간 미정";
  const payValue = m.job?.pay ?? m.job?.hourly_wage ?? m.job?.wage;
  const payText =
    payValue != null
      ? toCurrency(payValue)
      : m.job?.pay_text || m.job?.wage_text || m.pay_text || "협의";
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-bold text-gray-900">
            {m.job?.title || "-"}
          </h3>
          <p className="text-gray-600 text-sm mt-1">
            {time} · {place}
          </p>
          <p className="text-gray-700 text-sm mt-1">
            급여 {payText}
          </p>
        </div>
        <span className="text-sm text-gray-500">
          {m.status ? `상태: ${m.status}` : ""}
        </span>
      </div>
    </div>
  );
}

/** ---------------------------
 *  Apply Bottom Sheet
 *  -------------------------- */
function ApplySheet({ job, onClose, onSubmitted }) {
  const [note, setNote] = useState("잘 부탁드립니다.");
  const [submitting, setSubmitting] = useState(false);
  const displayPlace = job.place || job.location || job.address || "";
  const displayTime = job.time || job.schedule || job.shift || "";
  const payValue = job.pay ?? job.hourly_wage ?? job.wage;
  const payText = job.pay_text || (payValue != null ? `시급 ${toCurrency(payValue)}` : "");

  async function submit() {
    try {
      setSubmitting(true);
      await apiFetch(`/api/v1/applications`, {
        method: "POST",
        body: { job_id: job.id, note },
      });
      onSubmitted && onSubmitted();
      alert("지원이 완료되었어요.");
    } catch (e) {
      alert(parseApiError(e, "지원에 실패했어요. 다시 시도해 주세요."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[60]">
      {/* overlay */}
      <button
        aria-label="닫기"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      {/* sheet */}
      <div
        className="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl p-4"
        role="dialog"
        aria-modal="true"
      >
        <div className="mx-auto max-w-md">
          <div className="h-1 w-12 bg-gray-200 rounded-full mx-auto mb-3" />
          <h3 className="text-xl font-bold">{job.title}</h3>
          <p className="text-gray-600 text-sm mt-1">
            {displayTime} · {displayPlace} {payText ? `· ${payText}` : ""}
          </p>

          <label className="block text-sm text-gray-700 mt-4 mb-1">
            한 줄 메시지
          </label>
          <textarea
            className="w-full rounded-xl border p-3 text-gray-800"
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={120}
          />

          <div className="flex gap-2 mt-4">
            <button
              onClick={onClose}
              className="flex-1 h-12 rounded-xl bg-gray-100 text-gray-600 font-semibold"
            >
              취소
            </button>
            <button
              onClick={submit}
              disabled={submitting}
              className="flex-1 h-12 rounded-xl bg-emerald-600 text-white font-semibold disabled:opacity-60"
            >
              {submitting ? "제출중..." : "지원하기"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ApplicantSheet({ job, applicants, loading, error, onClose, onChangeStatus, actioningId }) {
  return (
    <div className="fixed inset-0 z-[70]">
      <button
        aria-label="닫기"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      <div className="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl p-5 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-xs text-gray-500">지원자 관리</p>
            <h3 className="text-xl font-bold text-gray-900">{job.title}</h3>
          </div>
          <button
            onClick={onClose}
            className="px-3 py-2 rounded-xl bg-gray-100 text-gray-600 font-semibold"
          >
            닫기
          </button>
        </div>
        {loading ? (
          <div className="py-6 text-center text-gray-500">불러오는 중...</div>
        ) : error ? (
          <div className="py-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-2xl px-4">
            {error}
          </div>
        ) : applicants.length === 0 ? (
          <div className="py-6 text-center text-gray-500">
            아직 지원한 사람이 없습니다.
          </div>
        ) : (
          <div className="space-y-3">
            {applicants.map((appl) => (
              <ApplicantCard
                key={appl.id}
                applicant={appl}
                onChangeStatus={onChangeStatus}
                actioning={actioningId === appl.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ApplicantCard({ applicant, onChangeStatus, actioning }) {
  const nickname =
    applicant.nickname ||
    applicant.name ||
    (applicant.phone_number
      ? `회원${applicant.phone_number.slice(-4)}`
      : "지원자");
  const region =
    applicant.region ||
    applicant.location ||
    (applicant.preferences?.region ?? "");
  const exp =
    applicant.experience ||
    applicant.preferences?.experiences ||
    applicant.preferences?.experience ||
    "";
  const status =
    applicant.status === "approved"
      ? "승인됨"
      : applicant.status === "rejected"
      ? "거절됨"
      : "대기";
  const history = applicant.match_info;

  return (
    <div className="border border-gray-100 rounded-2xl p-4 shadow-sm bg-white">
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-lg font-bold text-gray-900">{nickname}</p>
          <p className="text-sm text-gray-500">
            {region ? `${region} · ` : ""}
            {status}
          </p>
        </div>
        <span className="text-xs text-gray-400">
          {applicant.applied_at
            ? new Date(applicant.applied_at).toLocaleDateString()
            : ""}
        </span>
      </div>
      {exp ? (
        <p className="text-sm text-gray-700 leading-relaxed">{exp}</p>
      ) : null}
      {history && (
        <div className="mt-3 space-y-2">
          <div className="text-sm text-indigo-700 bg-indigo-50 rounded-xl px-3 py-2">
            <p>
              총 지원 {history.total_applications}회
              {history.last_applied_job ? ` · 최근 ${history.last_applied_job}` : ""}
            </p>
            {history.last_applied_at ? (
              <p className="text-xs text-indigo-600 mt-1">
                {new Date(history.last_applied_at).toLocaleDateString()}
              </p>
            ) : null}
          </div>
          {history.total_matches > 0 && (
            <div className="text-sm text-emerald-700 bg-emerald-50 rounded-xl px-3 py-2">
              <p>
                매칭 성사 {history.total_matches}회
                {history.last_matched_job ? ` · 최근 ${history.last_matched_job}` : ""}
              </p>
              {history.last_matched_at ? (
                <p className="text-xs text-emerald-600 mt-1">
                  {new Date(history.last_matched_at).toLocaleDateString()}
                </p>
              ) : null}
            </div>
          )}
        </div>
      )}
      {applicant.note ? (
        <p className="text-sm text-gray-500 bg-gray-50 rounded-xl px-3 py-2 mt-3">
          지원 메모: {applicant.note}
        </p>
      ) : null}
      <div className="mt-3 flex gap-2">
        <button
          disabled={applicant.status === "approved" || actioning}
          onClick={() => onChangeStatus?.(applicant.id, "approved")}
          className={`flex-1 h-10 rounded-xl font-semibold ${
            applicant.status === "approved"
              ? "bg-emerald-100 text-emerald-400 cursor-not-allowed"
              : "bg-emerald-500 text-white hover:bg-emerald-600"
          }`}
        >
          승인
        </button>
        <button
          disabled={applicant.status === "rejected" || actioning}
          onClick={() => onChangeStatus?.(applicant.id, "rejected")}
          className={`flex-1 h-10 rounded-xl font-semibold ${
            applicant.status === "rejected"
              ? "bg-red-100 text-red-400 cursor-not-allowed"
              : "bg-red-500 text-white hover:bg-red-600"
          }`}
        >
          거절
        </button>
      </div>
    </div>
  );
}
