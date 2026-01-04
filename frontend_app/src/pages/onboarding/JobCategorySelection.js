import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";

const BASE_URL = "http://127.0.0.1:8000";

export default function JobCategorySelection() {
  const navigate = useNavigate();
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [loading, setLoading] = useState(false);

  const categories = [
    { id: "apartment", label: "아파트 관리", icon: "🏢" },
    { id: "security", label: "경비/보안", icon: "👮" },
    { id: "cleaning", label: "청소/미화", icon: "🧹" },
    { id: "delivery", label: "택배 분류", icon: "📦" },
    { id: "food", label: "식당 보조", icon: "🍳" },
    { id: "cafe", label: "카페 보조", icon: "☕" },
    { id: "convenience", label: "편의점", icon: "🏪" },
    { id: "mart", label: "마트 보조", icon: "🛍️" },
    { id: "library", label: "도서관", icon: "📚" },
    { id: "office", label: "행정 보조", icon: "💼" },
    { id: "delivery2", label: "배달", icon: "🏍️" },
    { id: "etc", label: "기타", icon: "➕" },
  ];

  const toggleCategory = (id) => {
    setSelectedCategories((prev) =>
      prev.includes(id) ? prev.filter((cat) => cat !== id) : [...prev, id]
    );
  };

  const selectedLabels = selectedCategories
    .map((id) => categories.find((c) => c.id === id)?.label)
    .filter(Boolean);

  const getToken = () =>
    (typeof window !== "undefined" ? localStorage.getItem("access_token") : null) || "";

  const putHistory = async ({ experiences, none }) => {
    const token = getToken();
    if (!token) throw new Error("로그인 토큰이 없습니다.");
    const res = await fetch(`${BASE_URL}/api/v1/profile/prefs/history`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(none ? { none: true } : { experiences }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `저장 실패 (HTTP ${res.status})`);
    }
    return res.json().catch(() => ({}));
  };

  const saveAndNext = async () => {
    try {
      setLoading(true);
      await putHistory({ experiences: selectedLabels, none: false });
      navigate("/onboarding/capability");
    } catch (e) {
      alert(`저장 실패: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => navigate(-1);

  const skip = async () => {
    try {
      setLoading(true);
      await putHistory({ none: true });
      navigate("/onboarding/capability");
    } catch (e) {
      alert(`건너뛰기 실패: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[100dvh] bg-white flex flex-col overflow-y-auto">
      {/* 고정 헤더 + z-index */}
      <header className="fixed top-0 left-0 right-0 bg-white px-6 py-7 flex items-center justify-between border-b z-50">
        <button className="p-2" onClick={handleBack} type="button">
          <ChevronLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold">과거 이력 선택</h1>
        <button
          type="button"
          onClick={skip}
          className="text-black-500 font-medium text-base disabled:opacity-60"
          disabled={loading}
        >
          건너뛰기
        </button>
      </header>

      {/* 헤더 높이만큼 전체 콘텐츠 오프셋 */}
      <div className="mt-[92px]">
        {/* 프로그레스바 */}
        <div className="px-6 py-4">
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5, 6].map((step) => (
              <div
                key={step}
                className={`flex-1 h-2 rounded ${
                  step <= 4 ? "bg-orange-500" : "bg-gray-200"
                }`}
              />
            ))}
          </div>
          <p className="text-sm text-gray-500 mt-2 text-center">4/6 단계</p>
        </div>

        {/* 본문 */}
        <main className="flex-1 px-6 py-8 pb-32">
          <h2 className="text-3xl font-bold mb-2">
            이런 일을
            <br />
            해보신 적 있나요?
          </h2>
          <p className="text-gray-600 text-lg mb-8">
            경험이 있으시면 선택해주세요 (중복 가능)
          </p>

          <div className="grid grid-cols-2 gap-4">
            {categories.map((category) => {
              const isSelected = selectedCategories.includes(category.id);
              return (
                <button
                  key={category.id}
                  type="button"
                  onClick={() => toggleCategory(category.id)}
                  className={`relative p-4 rounded-2xl border-2 transition-all aspect-square ${
                    isSelected
                      ? "border-orange-500"
                      : "border-gray-200 bg-white hover:border-gray-300"
                  }`}
                >
                  <div className="mb-3 flex justify-center">
                    <div
                      className={`w-16 h-16 rounded-full flex items-center justify-center text-3xl ${
                        isSelected ? "bg-orange-500/10" : "bg-gray-100"
                      }`}
                    >
                      <span>{category.icon}</span>
                    </div>
                  </div>

                  <p
                    className={`text-base font-bold text-center ${
                      isSelected ? "text-black-500" : "text-gray-700"
                    }`}
                  >
                    {category.label}
                  </p>

                  {isSelected && (
                    <div className="absolute top-3 right-3 w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center">
                      <svg
                        className="w-4 h-4 text-white"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={3}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </main>
      </div>

      {/* 하단 버튼 */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t px-6 py-4">
        <button
          type="button"
          onClick={saveAndNext}
          disabled={selectedCategories.length === 0 || loading}
          className="w-full bg-orange-500 text-white font-bold text-xl py-5 rounded-xl disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-orange-600 transition"
        >
          {loading ? "저장 중..." : "다음"}
        </button>
      </div>
    </div>
  );
}