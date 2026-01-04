import React from "react";
import { ChevronLeft } from "lucide-react";
//하단바,상단바 고정용 컴포넌트

/**
 * props:
 * - title: 상단 가운데 타이틀
 * - onBack(): 뒤로가기
 * - rightNode: 상단 오른쪽(건너뛰기 등) 버튼/노드
 * - progress: { current: number, total: number }  // 진행바
 * - children: 본문
 * - footerNode: 하단 고정 영역(다음 버튼 등)
 * - maxWidth: 콘텐츠 최대폭(px) (기본 480)
 */
export default function OnboardingLayout({
  title,
  onBack,
  rightNode = <div className="w-10" />,
  progress,
  children,
  footerNode,
  maxWidth = 480,
}) {
  // 고정 영역 높이 (본문 보정용)
  const HEADER_H = 64; // px (py-4 + 폰트 라인 높이 기준)
  const FOOTER_H = 88; // px (py-4 + 버튼 높이)

  return (
    <div className="min-h-screen bg-white relative">
      {/* 상단바 (고정) */}
      <header className="fixed top-0 left-0 right-0 z-40 bg-white border-b">
        <div
          className="px-6 py-4 mx-auto flex items-center justify-between"
          style={{ maxWidth }}
        >
          <button type="button" onClick={onBack} className="p-2">
            <ChevronLeft className="w-6 h-6" />
          </button>
          <h1 className="text-lg font-bold">{title}</h1>
          {rightNode}
        </div>
        {progress?.total ? (
          <div className="px-6 pb-3 pt-1 mx-auto" style={{ maxWidth }}>
            <div className="flex gap-1">
              {Array.from({ length: progress.total }, (_, i) => i + 1).map(
                (i) => (
                  <div
                    key={i}
                    className={`flex-1 h-2 rounded ${
                      i <= progress.current ? "bg-orange-500" : "bg-gray-200"
                    }`}
                  />
                )
              )}
            </div>
            <p className="text-sm text-gray-500 mt-2 text-center">
              {progress.current}/{progress.total} 단계
            </p>
          </div>
        ) : null}
      </header>

      {/* 본문 (스크롤 영역) */}
      <main
        className="px-6 mx-auto overflow-y-auto"
        style={{
          maxWidth,
          marginTop: progress ? HEADER_H + 64 : HEADER_H, // 진행바 있으면 여유를 조금 더
          marginBottom: FOOTER_H,
          paddingTop: 16,
          paddingBottom: 16,
          minHeight: `calc(100vh - ${HEADER_H + FOOTER_H}px)`,
        }}
      >
        {children}
      </main>

      {/* 하단바 (고정) */}
      <footer className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t">
        <div className="px-6 py-4 mx-auto" style={{ maxWidth }}>
          {footerNode}
        </div>
      </footer>
    </div>
  );
}