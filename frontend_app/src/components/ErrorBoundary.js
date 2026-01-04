import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    // 필요하면 로깅
    console.error("[ErrorBoundary]", error, info);
  }
  handleReset = () => {
    this.setState({ hasError: false, error: null });
    // 가장 안전: 전체 새로고침 또는 콜백
    if (this.props.onReset) this.props.onReset();
  };
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen grid place-items-center p-6">
          <div className="max-w-md w-full p-5 rounded-2xl border shadow-sm bg-white">
            <h2 className="text-lg font-semibold">문제가 발생했어요</h2>
            <p className="text-sm text-gray-500 mt-1">
              잠시 후 다시 시도하거나, 아래 버튼으로 초기화해 주세요.
            </p>
            <pre className="mt-3 p-3 bg-gray-50 rounded text-xs overflow-auto">
              {String(this.state.error)}
            </pre>
            <div className="mt-4 flex gap-2">
              <button
                className="px-4 py-2 rounded-xl bg-gray-900 text-white text-sm"
                onClick={() => window.location.reload()}
              >
                새로고침
              </button>
              <button
                className="px-4 py-2 rounded-xl bg-gray-200 text-sm"
                onClick={this.handleReset}
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}