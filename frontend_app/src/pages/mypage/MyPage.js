// src/pages/mypage/MyPage.js
import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import BottomNav from "../../components/BottomNav";

import { ApiError, ProfileAPI, parseApiError } from "../../utils/apiClient";

/** ===== 작은 UI 컴포넌트들 ===== */
function Icon({ name, className = "w-5 h-5" }) {
  switch (name) {
    case "location":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.5-7.5 11.25-7.5 11.25S4.5 18 4.5 10.5a7.5 7.5 0 1115 0z" />
        </svg>
      );
    case "clock":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l3 3" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case "bag":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M16 11V7a4 4 0 10-8 0v4M4 9h16l-1 10a2 2 0 01-2 2H7a2 2 0 01-2-2L4 9z" />
        </svg>
      );
    case "muscle":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 15s1.5-2 4-2c2.5 0 3.5 2 6 2s4-2 4-2-1.5 5-10 5-4-3-4-3z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 11V7a3 3 0 013-3h1" />
        </svg>
      );
    case "chevron":
      return (
        <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      );
    case "user":
      return (
        <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 20.25a8.25 8.25 0 0115 0" />
        </svg>
      );
    case "bell":
      return (
        <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 10-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.73 21a2 2 0 01-3.46 0" />
        </svg>
      );
    case "shield":
      return (
        <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 3l7 4v6c0 5-3.5 7.5-7 8-3.5-.5-7-3-7-8V7l7-4z" />
        </svg>
      );
    case "gear":
      return (
        <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317a1 1 0 011.35-.937 8.001 8.001 0 015.256 5.256 1 1 0 01-.936 1.35l-.726.121a2 2 0 00-1.515 1.515l-.121.726a1 1 0 01-1.35.936 8.001 8.001 0 01-5.256-5.256 1 1 0 01.937-1.35l.726-.121a2 2 0 001.515-1.515l.121-.726z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      );
    case "logout":
      return (
        <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3H6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 006 21h7.5a2.25 2.25 0 002.25-2.25V15" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M18 12H9m9 0l-3 3m3-3l-3-3" />
        </svg>
      );
    default:
      return null;
  }
}

function Card({ children, className = "" }) {
  return (
    <div className={`bg-white rounded-2xl border border-gray-100 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

function Section({ icon, title, children, onClickEdit }) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-gray-800">
          {/* 🔶 섹션 아이콘 오렌지 컬러 */}
          <Icon name={icon} className="w-5 h-5 text-orange-500" />
          <h3 className="text-base font-semibold">{title}</h3>
        </div>
        {onClickEdit ? (
          <button onClick={onClickEdit} className="text-sm text-gray-500 hover:text-gray-700">
            수정
          </button>
        ) : null}
      </div>
      {children}
    </Card>
  );
}

function Pill({ children }) {
  return (
    <span className="px-3 py-1.5 rounded-full bg-gray-100 text-gray-700 text-sm">
      {children}
    </span>
  );
}

function ListItem({ icon, title, danger = false, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full flex items-center justify-between px-4 py-4 ${danger ? "text-red-600" : "text-gray-800"}`}
    >
      <div className="flex items-center gap-3">
        {/* 🔶 리스트 아이콘 기본 오렌지, danger는 빨강 */}
        <Icon
          name={icon}
          className={`w-5 h-5 ${danger ? "text-red-600" : "text-orange-500"}`}
        />
        <span className="text-[15px]">{title}</span>
      </div>
      <Icon name="chevron" className="w-5 h-5 text-gray-400" />
    </button>
  );
}

function EditModal({ title, children, onClose, onSave, saving, error }) {
  return (
    <div className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full max-w-md bg-white rounded-t-3xl sm:rounded-2xl shadow-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <button
            type="button"
            aria-label="닫기"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>
        <div className="space-y-4 text-sm text-gray-800">{children}</div>
        {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
        <div className="mt-6 flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 h-11 rounded-xl border border-gray-200 text-gray-600"
          >
            취소
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            className="flex-1 h-11 rounded-xl bg-orange-500 text-white font-semibold disabled:opacity-60"
          >
            {saving ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}

/** ===== 페이지 컴포넌트 ===== */
export default function MyPage() {
  const nav = useNavigate();

  const [loading, setLoading] = useState(true);
  // 표시용 상태
  const [regions, setRegions] = useState([]);
  const [days, setDays] = useState([]);
  const [timeSlots, setTimeSlots] = useState([]);
  const [experiences, setExperiences] = useState([]);
  const [activityNote, setActivityNote] = useState("적당한 활동이 좋아요");
  const [physicalLevel, setPhysicalLevel] = useState("medium");
  const [nickname, setNickname] = useState("");
  const [phone, setPhone] = useState("");
  const [editSection, setEditSection] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [editError, setEditError] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  const handleBack = () => nav(-1);
  const handleSkip = () => nav("/"); // 필요시 다른 경로로 변경 가능

  const applyProfileSummary = useCallback((data) => {
    if (!data) return;
    const account = data.account || {};
    const prefs = data.prefs || {};
    const locationPref = prefs.location || {};
    const normalizedRegions = prefs.regions || locationPref.regions || [];

    setNickname(account.nickname || data.nickname || "사용자");
    setPhone(account.phone || data.account?.phone || "");
    setRegions(normalizedRegions);
    setDays(prefs.days || []);
    setTimeSlots(prefs.time_slots || []);
    setExperiences(prefs.experiences || data.experiences || []);

    const level = prefs.physical_level || data.physical_level || "medium";
    setPhysicalLevel(level || "medium");
    setActivityNote(
      level === "high"
        ? "활동적인 업무도 가능해요"
        : level === "low"
        ? "무리가 적은 일이 좋아요"
        : "적당한 활동이 좋아요"
    );
  }, []);

  const editTitles = {
    location: "선호 지역 수정",
    time: "선호 시간/요일 수정",
    history: "과거 경험 수정",
    capability: "신체 활동 수준 수정",
  };

  const parseCommaList = useCallback((text = "") => {
    return text
      .split(/[,\\n]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }, []);

  const openEdit = (section) => {
    setEditError("");
    switch (section) {
      case "location":
        setEditValues({ regionsText: regions.join(", ") });
        break;
      case "time":
        setEditValues({
          daysText: days.join(", "),
          slotsText: timeSlots.join(", "),
        });
        break;
      case "history":
        setEditValues({
          experiencesText: experiences.join(", "),
          noExperience: experiences.length === 0,
        });
        break;
      case "capability":
        setEditValues({ physicalLevel: physicalLevel || "medium" });
        break;
      default:
        setEditValues({});
    }
    setEditSection(section);
  };

  const closeEdit = (force = false) => {
    if (!force && savingEdit) return;
    setEditSection(null);
    setEditValues({});
    setEditError("");
  };

  const handleSaveEdit = async () => {
    if (!editSection) return;
    setSavingEdit(true);
    setEditError("");
    try {
      let response;
      if (editSection === "location") {
        const regionList = parseCommaList(editValues.regionsText || "");
        if (!regionList.length) {
          setEditError("최소 한 개 이상의 지역을 입력해주세요.");
          setSavingEdit(false);
          return;
        }
        response = await ProfileAPI.updateLocation({
          use_gps: false,
          regions: regionList,
        });
      } else if (editSection === "time") {
        const dayList = parseCommaList(editValues.daysText || "");
        const slotList = parseCommaList(editValues.slotsText || "");
        if (!dayList.length || !slotList.length) {
          setEditError("요일과 시간대를 모두 입력해주세요.");
          setSavingEdit(false);
          return;
        }
        response = await ProfileAPI.updateTime({
          days: dayList,
          time_slots: slotList,
        });
      } else if (editSection === "history") {
        const expList = parseCommaList(editValues.experiencesText || "");
        const noExp = !!editValues.noExperience;
        if (!noExp && !expList.length) {
          setEditError("경험을 쉼표로 구분해 입력하거나 '경험이 없어요'를 선택해주세요.");
          setSavingEdit(false);
          return;
        }
        response = await ProfileAPI.updateHistory({
          experiences: expList,
          none: noExp,
        });
      } else if (editSection === "capability") {
        const level = editValues.physicalLevel || physicalLevel || "medium";
        response = await ProfileAPI.updateCapability({
          physical_level: level,
        });
      }

      if (response) {
        applyProfileSummary(response);
      }
      closeEdit(true);
    } catch (e) {
      setEditError(parseApiError(e, "수정에 실패했어요. 다시 시도해주세요."));
    } finally {
      setSavingEdit(false);
    }
  };

  const renderEditFields = () => {
    switch (editSection) {
      case "location":
        return (
          <>
            <label className="text-sm font-medium text-gray-700">
              선호 지역 (쉼표로 구분)
            </label>
            <textarea
              className="w-full rounded-2xl border border-gray-200 p-3"
              rows={3}
              value={editValues.regionsText || ""}
              onChange={(e) =>
                setEditValues((prev) => ({ ...prev, regionsText: e.target.value }))
              }
              placeholder="예: 성동구, 광진구"
            />
            <p className="text-xs text-gray-400">
              최대 5개까지 입력할 수 있어요.
            </p>
          </>
        );
      case "time":
        return (
          <>
            <label className="text-sm font-medium text-gray-700">
              선호 요일 (쉼표로 구분)
            </label>
            <textarea
              className="w-full rounded-2xl border border-gray-200 p-3"
              rows={2}
              value={editValues.daysText || ""}
              onChange={(e) =>
                setEditValues((prev) => ({ ...prev, daysText: e.target.value }))
              }
              placeholder="예: 월요일, 수요일, 금요일"
            />
            <label className="text-sm font-medium text-gray-700">
              선호 시간대
            </label>
            <textarea
              className="w-full rounded-2xl border border-gray-200 p-3"
              rows={2}
              value={editValues.slotsText || ""}
              onChange={(e) =>
                setEditValues((prev) => ({ ...prev, slotsText: e.target.value }))
              }
              placeholder="예: 오전, 오후"
            />
          </>
        );
      case "history":
        return (
          <>
            <label className="text-sm font-medium text-gray-700">
              경험한 일 (쉼표로 구분)
            </label>
            <textarea
              className="w-full rounded-2xl border border-gray-200 p-3"
              rows={3}
              value={editValues.experiencesText || ""}
              onChange={(e) =>
                setEditValues((prev) => ({
                  ...prev,
                  experiencesText: e.target.value,
                }))
              }
              placeholder="예: 아파트 관리, 청소/미화"
              disabled={editValues.noExperience}
            />
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={!!editValues.noExperience}
                onChange={(e) =>
                  setEditValues((prev) => ({
                    ...prev,
                    noExperience: e.target.checked,
                  }))
                }
              />
              경험이 없어요
            </label>
          </>
        );
      case "capability":
        const options = [
          { value: "high", label: "활동적", desc: "걷기/움직임이 많은 일도 괜찮아요" },
          { value: "medium", label: "보통", desc: "적당히 몸을 쓰는 일이 좋아요" },
          { value: "low", label: "조용한 일", desc: "무리가 적은 일이 좋아요" },
        ];
        return (
          <div className="space-y-2">
            {options.map((opt) => {
              const selected =
                (editValues.physicalLevel || physicalLevel || "medium") === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() =>
                    setEditValues((prev) => ({
                      ...prev,
                      physicalLevel: opt.value,
                    }))
                  }
                  className={`w-full text-left border rounded-2xl px-4 py-3 ${
                    selected
                      ? "border-orange-500 bg-orange-50"
                      : "border-gray-200 bg-white"
                  }`}
                >
                  <div className="font-semibold">{opt.label}</div>
                  <div className="text-xs text-gray-500 mt-1">{opt.desc}</div>
                </button>
              );
            })}
          </div>
        );
      default:
        return null;
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const data = await ProfileAPI.summary();
        applyProfileSummary(data);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          alert("로그인이 필요합니다. 다시 로그인해주세요.");
          nav("/login");
          return;
        }
        console.warn("[MyPage] 서버 실패 → 더미 데이터로 대체:", parseApiError(e));
        const dummy = {
          account: {
            nickname: "홍길동",
            phone: "010-0000-0000",
            region: "서울",
            avatar_url: "",
          },
          prefs: {
            location: { use_gps: false, regions: ["성동구", "광진구", "강남구"] },
            regions: ["성동구", "광진구", "강남구"],
            days: ["월요일 오전", "수요일 오전", "금요일 오전"],
            time_slots: ["오전"],
            experiences: ["아파트 관리", "경비/보안", "청소/미화"],
            physical_level: "medium",
          },
        };
        applyProfileSummary(dummy);
      } finally {
        setLoading(false);
      }
    })();
  }, [applyProfileSummary, nav]);

  if (loading) {
    return (
      <div className="min-h-[100dvh] bg-gray-50">
        {/* 고정 상단바 (로딩 상태도 동일 헤더 사용) */}
        <header className="fixed top-0 left-0 right-0 bg-white px-6 py-7 flex items-center justify-between border-b z-50">
          <button onClick={handleBack} className="p-2">
            <ChevronLeft className="w-6 h-6" />
          </button>
          <h1 className="text-xl font-bold">나의 정보</h1>
        </header>

        {/* 헤더 오프셋 */}
        <main className="max-w-md mx-auto p-4 space-y-4 mt-[92px]">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 bg-white border rounded-2xl shadow-sm animate-pulse" />
          ))}
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-[100dvh] bg-[#F7F8FA]">
      {/* ✅ 고정 상단바 */}
      <header className="fixed top-0 left-0 right-0 bg-white px-6 py-7 flex items-center justify-between border-b z-50">
        <button onClick={handleBack} className="p-2">
          <ChevronLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold">나의 정보</h1>
        <button onClick={handleSkip} className="text-black-500 font-medium text-base">
          
        </button>
      </header>

      {/* 헤더 높이만큼 오프셋 */}
      <main className="max-w-md mx-auto p-4 space-y-4 mt-[92px]">
        {/* 프로필 카드 */}
        <Card className="p-4">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-gray-100 grid place-items-center border">
                {/* 🔶 프로필 기본 아이콘도 오렌지 */}
                <Icon name="user" className="w-8 h-8 text-orange-500" />
              </div>
              <button
                className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-white border grid place-items-center shadow"
                onClick={() => alert("프로필 이미지 변경")}
                aria-label="change avatar"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536M9 11l6-6 3.536 3.536-6 6H9v-3.536z" />
                </svg>
              </button>
            </div>

            <div className="flex-1">
              <div className="font-bold text-[16px]">{nickname || "사용자"}</div>
              <div className="text-sm text-gray-500 mt-0.5">{phone || "전화번호 미입력"}</div>
              <div className="text-xs text-gray-400 mt-1">나의 기본 정보</div>
            </div>
          </div>
        </Card>

        {/* 선호 지역 */}
        <Section icon="location" title="선호 지역" onClickEdit={() => openEdit("location")}>
          <div className="flex flex-wrap gap-2">
            {regions.length ? regions.map((r) => <Pill key={r}>{r}</Pill>) : <span className="text-sm text-gray-400">미설정</span>}
          </div>
        </Section>

        {/* 선호 시간/요일 */}
        <Section icon="clock" title="선호 시간/요일" onClickEdit={() => openEdit("time")}>
          <div className="flex flex-wrap gap-2">
            {days.concat(timeSlots).length ? (
              <>
                {days.map((d) => <Pill key={`d-${d}`}>{d}</Pill>)}
                {timeSlots.map((t) => <Pill key={`t-${t}`}>{t}</Pill>)}
              </>
            ) : (
              <span className="text-sm text-gray-400">미설정</span>
            )}
          </div>
        </Section>

        {/* 과거 경험 */}
        <Section icon="bag" title="과거 경험" onClickEdit={() => openEdit("history")}>
          <div className="flex flex-wrap gap-2">
            {experiences.length ? experiences.map((x) => <Pill key={x}>{x}</Pill>) : <span className="text-sm text-gray-400">경험 없음</span>}
          </div>
        </Section>

        {/* 신체 활동 수준 */}
        <Section icon="muscle" title="신체 활동 수준" onClickEdit={() => openEdit("capability")}>
          <p className="text-sm text-gray-800">{activityNote}</p>
        </Section>

        {/* 설정 리스트 */}
        <Card>
          <ul className="divide-y divide-gray-100">
            <li>
              <ListItem icon="user" title="계정 관리" onClick={() => nav("/mypage/account")} />
            </li>
            <li>
              <ListItem icon="bell" title="알림 설정" onClick={() => alert("알림 설정")} />
            </li>
            <li>
              <ListItem icon="shield" title="PIN 변경" onClick={() => nav("/mypage/pin")} />
            </li>
            <li>
              <ListItem icon="gear" title="설정" onClick={() => alert("앱 설정")} />
            </li>
            <li className="bg-red-50/40 rounded-b-2xl">
              <ListItem
                icon="logout"
                title="로그아웃"
                danger
                onClick={() => {
                  localStorage.removeItem("access_token");
                  localStorage.removeItem("refresh_token");
                  nav("/", { replace: true });
                }}
              />
            </li>
          </ul>
        </Card>

        {/* 푸터 버전 정보 */}
        <div className="py-8 text-center text-xs text-gray-400">
          일로와 버전 1.0.0
          <br />© 2025 일로와. All rights reserved.
        </div>
      </main>

      <BottomNav />

      {editSection && (
        <EditModal
          title={editTitles[editSection] || "정보 수정"}
          onClose={() => closeEdit()}
          onSave={handleSaveEdit}
          saving={savingEdit}
          error={editError}
        >
          {renderEditFields()}
        </EditModal>
      )}
    </div>
  );
}
