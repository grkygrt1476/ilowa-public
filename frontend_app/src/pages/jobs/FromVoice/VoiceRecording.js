// 음성 입력하는 페이지 -> 임시 저장 및 예시 페이지 이동
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronLeft,
  Loader2,
  Mic,
  Send,
  Sparkles,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import {
  AIAPI,
  MediaAPI,
  getStoredToken,
  parseApiError,
} from "../../../utils/apiClient";

const STORAGE_KEY = "voiceRecordingData";

const parseStoredRecords = (raw) => {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed;
    if (parsed && typeof parsed === "object") return [parsed];
  } catch (e) {
    console.error("storage parse failed", e);
  }
  return [];
};

const joinDays = (post) => {
  if (Array.isArray(post?.schedule_days) && post.schedule_days.length) {
    return post.schedule_days.join(", ");
  }
  return post?.frequency || post?.schedule || "";
};

const normalizeTime = (value) => {
  if (!value) return "";
  if (value.includes(":")) return value.slice(0, 5);
  if (/^\d{1,2}$/.test(value)) return `${value.padStart(2, "0")}:00`;
  return value;
};

const timeRange = (post) => {
  const start = normalizeTime(post?.start_time);
  const end = normalizeTime(post?.end_time);
  if (start || end) return `${start || "?"} ~ ${end || "?"}`;
  if (Array.isArray(post?.time_slots) && post.time_slots.length) {
    return post.time_slots.join(", ");
  }
  return post?.time || "";
};

const wageText = (post) => {
  if (post?.wage_amount) return post.wage_amount;
  if (post?.hourly_wage) return `${Number(post.hourly_wage).toLocaleString()}원`;
  return "";
};

const MISSING_FIELD_LABELS = {
  title: "공고 제목",
  region: "지역",
  schedule_days: "근무 요일",
  start_time: "시작 시간",
  end_time: "종료 시간",
  participants: "모집 인원",
  hourly_wage: "시급",
  description: "상세 설명",
  address: "주소",
};

const mapVoicePostToTemplate = (post = {}) => ({
  title: post.title || "",
  category: post.category || "",
  location: post.address || post.region || "",
  schedule: joinDays(post),
  time: timeRange(post),
  duration: post.duration || "",
  pay: wageText(post),
  requirements: Array.isArray(post?.qualifications)
    ? post.qualifications.join("\n")
    : post?.qualifications || "",
  description: post.description || post.raw_text || "",
});

export default function VoiceRecording() {
  const nav = useNavigate();
  const [isRecording, setIsRecording] = useState(false);
  const [blob, setBlob] = useState(null);
  const [errMsg, setErrMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const [savedRecords, setSavedRecords] = useState([]);
  const [sessionPost, setSessionPost] = useState(null);
  const [missingFields, setMissingFields] = useState([]);
  const [conversation, setConversation] = useState([]);
  const [activePrompt, setActivePrompt] = useState("");

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const questionSignatureRef = useRef("");

  const voiceTranscript = useMemo(() => {
    return conversation
      .filter((entry) => entry.role === "user" && entry.method === "voice" && entry.text?.trim())
      .map((entry) => entry.text.trim())
      .join("\n\n");
  }, [conversation]);
  const hasPendingRecording = useMemo(
    () => Boolean(blob && !voiceTranscript && !isRecording),
    [blob, voiceTranscript, isRecording],
  );

  const essentialChecks = useMemo(() => {
    const fields = [
      { id: "title", label: "일 제목", value: sessionPost?.title },
      {
        id: "address",
        label: "주소",
        value: sessionPost?.address || sessionPost?.region || sessionPost?.location || "",
      },
      { id: "wage", label: "임금", value: wageText(sessionPost) },
      {
        id: "schedule",
        label: "날짜 / 요일",
        value: joinDays(sessionPost) || sessionPost?.schedule || sessionPost?.time || "",
      },
      {
        id: "activity",
        label: "하는 활동",
        value: sessionPost?.description || sessionPost?.raw_text || "",
      },
    ];

    return fields.map((item) => {
      const raw =
        typeof item.value === "number" ? String(item.value) : (item.value || "").toString();
      const cleaned = raw.trim();
      return {
        ...item,
        display: cleaned || "미입력",
        filled: Boolean(cleaned),
      };
    });
  }, [sessionPost]);

  const missingFieldText = useMemo(() => {
    if (!missingFields?.length) return "";
    return missingFields
      .map((field) => MISSING_FIELD_LABELS[field] || field)
      .join(", ");
  }, [missingFields]);
  const promptMessage = useMemo(() => {
    if (isRecording) {
      return activePrompt
        ? `"${activePrompt}" 질문에 대한 답변을 듣고 있어요`
        : "마이크 버튼을 다시 눌러 녹음을 종료하세요";
    }
    if (voiceTranscript) return voiceTranscript;
    if (hasPendingRecording) return "녹음이 완료됐어요! 아래 'AI 초안 만들기' 버튼을 눌러주세요.";
    return '예: "반려견 산책을 주 3회 도와줄 분을 찾고 있어요. 시급은 15,000원이에요."';
  }, [isRecording, activePrompt, voiceTranscript, hasPendingRecording]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    };
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    const records = parseStoredRecords(stored);
    if (records.length) setSavedRecords(records);
  }, []);

  const persistRecording = async (audioBlob) => {
    const timestamp = Date.now();
    const filename = `record_${timestamp}.webm`;
    const file = new File([audioBlob], filename, {
      type: audioBlob.type || "audio/webm",
    });
    const uploadRes = await MediaAPI.uploadAudio(file);
    const uploadId = uploadRes?.upload_ids?.[0];
    if (!uploadId) throw new Error("업로드 식별자를 받지 못했어요.");

    const payload = {
      savedAt: new Date().toISOString(),
      size: audioBlob.size,
      type: file.type,
      filename,
      uploadId,
      previewUrl: uploadRes?.urls?.[0] || null,
    };
    setSavedRecords((prev) => {
      const nextRecords = [payload, ...prev];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextRecords));
      return nextRecords;
    });
    return payload;
  };

  const handleBack = () => {
    if (window.history.length > 1) nav(-1);
    else nav("/");
  };

  const startRecording = async (promptLabel = "") => {
    setErrMsg("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        const recorded = new Blob(chunksRef.current, { type: "audio/webm" });
        setBlob(recorded);
      };
      mediaRecorderRef.current = mr;
      mr.start();
      setActivePrompt(promptLabel);
      setIsRecording(true);
    } catch (e) {
      setErrMsg("마이크 권한이 필요합니다.");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const toggleRecording = (promptLabel = "") => {
    if (isRecording) stopRecording();
    else startRecording(promptLabel);
  };

  const sendToPipeline = async ({ uploadId, manualText = "", method = "voice" }) => {
    const body = {};
    if (sessionPost) body.existing_post = sessionPost;
    if (uploadId) body.upload_id = uploadId;
    if (manualText) body.clarification_text = manualText;

    const data = await AIAPI.createPostFromVoice(body);
    if (!data?.post) throw new Error("AI 응답이 비어 있습니다.");

    const transcript = method === "text" ? manualText : (data.transcript || manualText);
    setSessionPost(data.post);
    setMissingFields(data.missing_fields || []);

    setConversation((prev) => {
      const next = [...prev];
      if (transcript) {
        next.push({
          id: `${Date.now()}_${method}_${Math.random().toString(36).slice(2)}`,
          role: "user",
          text: transcript,
          method,
          question: activePrompt || undefined,
          timestamp: new Date().toISOString(),
        });
      }

      if (data.needs_clarification) {
        questionSignatureRef.current = "pending";
      } else if (questionSignatureRef.current) {
        questionSignatureRef.current = "";
        next.push({
          id: `${Date.now()}_ai_complete`,
          role: "ai",
          text: "필요한 정보가 모두 준비됐어요! 아래 초안을 확인해보세요.",
          method: "status",
          timestamp: new Date().toISOString(),
        });
      }

      return next;
    });

    setBlob(null);
    setActivePrompt("");
  };

  const processAudioBlob = async () => {
    const token = getStoredToken();
    if (!token) { setErrMsg("로그인이 필요합니다. 먼저 로그인해주세요."); return; }
    if (!blob) { setErrMsg("녹음된 내용이 없습니다."); return; }

    setErrMsg("");
    setLoading(true);
    try {
      const saved = await persistRecording(blob);
      await sendToPipeline({ uploadId: saved.uploadId, method: "voice" });
    } catch (e) {
      setErrMsg(parseApiError(e, "녹음 데이터를 처리하지 못했어요. 다시 시도해주세요."));
    } finally {
      setLoading(false);
    }
  };

  const goToTemplateReview = () => {
    if (!sessionPost) return;
    nav("/jobs/from-image/review", {
      state: { mapped_fields: mapVoicePostToTemplate(sessionPost) },
    });
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <header className="px-6 py-4 flex items-center border-b">
        <button onClick={handleBack} className="p-2"><ChevronLeft className="w-6 h-6" /></button>
        <h1 className="text-lg font-bold ml-4">음성으로 공고 작성</h1>
      </header>

      <main className="flex-1 px-6 py-6 pb-32 space-y-6">
        {errMsg && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 whitespace-pre-line">
            {errMsg}
          </div>
        )}

        <section className="bg-[#FEF3E2] rounded-2xl p-6 text-center">
          <p className="text-sm text-[#A8641D] font-semibold mb-2">
            {isRecording ? "듣고 있어요..." : "필요한 일을 말씀해주세요"}
          </p>
          <p className="text-gray-700 whitespace-pre-line text-lg">
            {promptMessage}
          </p>

          <button
            disabled={loading}
            onClick={() => toggleRecording()}
            className={`mx-auto mt-6 w-40 h-40 rounded-full shadow-2xl flex items-center justify-center transition-all ${
              isRecording ? "bg-red-500 animate-pulse" : "bg-[#F4BA4D] hover:bg-[#E5AB3D]"
            } ${loading ? "opacity-60" : ""}`}
          >
            <Mic className="w-20 h-20 text-white" strokeWidth={2} />
          </button>
          {activePrompt && !isRecording && (
            <p className="text-sm text-gray-600 mt-3">
              "{activePrompt}" 질문에 대한 답변을 들려주세요.
            </p>
          )}

          {blob && (
            <button
              onClick={processAudioBlob}
              disabled={loading}
              className="mt-6 inline-flex items-center gap-2 bg-[#F4BA4D] text-white font-semibold text-lg px-6 py-3 rounded-xl hover:bg-[#E5AB3D] transition disabled:opacity-60"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              <span>{sessionPost ? "추가 설명 전달하기" : "AI 초안 만들기"}</span>
            </button>
          )}
        </section>

        {voiceTranscript && (
          <section className="bg-white rounded-2xl border border-gray-100 p-5 space-y-3">
            <div className="text-sm font-semibold text-gray-700">입력한 내용</div>
            <p className="whitespace-pre-line text-gray-900 leading-relaxed text-base">
              {voiceTranscript}
            </p>
            {missingFieldText && (
              <p className="text-sm text-[#B45309] bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
                부족한 내용이 있어요: {missingFieldText}. 해당 정보를 다시 말씀해주세요.
              </p>
            )}
          </section>
        )}

        {sessionPost && (
          <section className="bg-white rounded-2xl border border-gray-100 p-5 space-y-4">
            <div className="flex items-center gap-2 text-gray-700 font-semibold">
              <Sparkles className="w-5 h-5 text-[#F4BA4D]" />
              <span>필수 항목 충족 현황</span>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {essentialChecks.map((item) => (
                <div
                  key={item.id}
                  className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3"
                >
                  <p className="text-xs text-gray-500">{item.label}</p>
                  <p
                    className={`mt-2 text-2xl font-extrabold ${
                      item.filled ? "text-green-600" : "text-gray-900"
                    }`}
                  >
                    {item.display}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {sessionPost && (
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4">
            <div className="flex items-center gap-2 text-[#F4BA4D] font-semibold">
              <Sparkles className="w-5 h-5" />
              <span>AI가 채워준 초안</span>
            </div>
            <div className="grid grid-cols-1 gap-3">
              {[
                ["공고 제목", sessionPost.title || "-"],
                ["근무 지역", sessionPost.address || sessionPost.region || "-"],
                ["근무 일정", joinDays(sessionPost) || "-"],
                ["근무 시간", timeRange(sessionPost) || "-"],
                ["모집 인원", sessionPost.participants ? `${sessionPost.participants}명` : "-"],
                ["급여", wageText(sessionPost) || "-"],
              ].map(([label, value]) => (
                <div key={label} className="bg-gray-50 rounded-xl px-4 py-3">
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className="text-base font-semibold mt-1">{value || "-"}</p>
                </div>
              ))}
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">상세 설명</p>
              <p className="whitespace-pre-line text-sm text-gray-800 bg-gray-50 rounded-xl px-4 py-3">
                {sessionPost.description || sessionPost.raw_text || "아직 설명이 부족해요."}
              </p>
            </div>
            {Array.isArray(sessionPost?.qualifications) && sessionPost.qualifications.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 mb-1">지원 자격</p>
                <ul className="list-disc list-inside text-sm text-gray-800 bg-gray-50 rounded-xl px-4 py-3">
                  {sessionPost.qualifications.map((item, idx) => (
                    <li key={`${item}-${idx}`}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        <section className="bg-gray-50 rounded-2xl p-5 space-y-3">
          <p className="text-sm font-semibold text-gray-700">진행 기록</p>
          {conversation.length === 0 ? (
            <p className="text-gray-500 text-sm">녹음하거나 텍스트를 보내면 여기에 기록돼요.</p>
          ) : (
            <div className="space-y-3">
              {conversation.map((entry) => (
                <div
                  key={entry.id}
                  className={`rounded-2xl px-4 py-3 text-sm whitespace-pre-line ${
                    entry.role === "user" ? "bg-white shadow border border-gray-100" : "bg-[#FFF6EC]"
                  }`}
                >
                  <p className="text-xs uppercase tracking-wide text-gray-400 mb-1">
                    {entry.role === "user"
                      ? entry.method === "text"
                        ? "내 텍스트 입력"
                        : "내 음성(STT)"
                      : "AI 안내"}
                    {entry.question ? ` · ${entry.question}` : ""}
                  </p>
                  <p className="text-gray-800">{entry.text}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      <div className="fixed bottom-0 left-0 right-0 bg-white border-t px-6 py-4">
        <div className="flex flex-col gap-3">
          <button
            onClick={goToTemplateReview}
            disabled={!sessionPost}
            className="w-full bg-[#F4BA4D] text-white font-bold text-lg py-4 rounded-xl hover:bg-[#E5AB3D] transition disabled:opacity-50"
          >
            {sessionPost ? "AI 초안 확인 / 수정하기" : "먼저 음성을 녹음해주세요"}
          </button>
          {savedRecords.length > 0 && (
            <button
              onClick={() => nav("/jobs/from-image/review")}
              className="w-full text-[#F4BA4D] font-semibold text-base py-3 rounded-xl border-2 border-[#F4BA4D] hover:bg-[#FEF3E2] transition"
            >
              최근 예시 공고 페이지 이동
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
