// src/App.js
import React from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";

// --- 페이지들 ---
import Main from "./components/Main";
import RegisterFlow from "./pages/register/RegisterFlow";
import Login from "./pages/auth/Login";

// 온비딩 페이지
import Nickname from "./pages/onboarding/Nickname";
import Location from "./pages/onboarding/Location";
import Time from "./pages/onboarding/Time";
import JobCategorySelection from "./pages/onboarding/JobCategorySelection";
import Capability from "./pages/onboarding/Capability";
import OnboardingSummary from "./pages/onboarding/OnboardingSummary";

import MainHome from "./pages/main/MainHome";
import MyPage from "./pages/mypage/MyPage";

import BottomNav from "./components/BottomNav";

//음성 기반
import VoiceRecording from "./pages/jobs/FromVoice/VoiceRecording";
import JobPostTemplate from "./pages/jobs/Template/JobPost";

//이미지 기반
import ImageUpload from "./pages/jobs/FromImage/ImageUpload";

//직접 등록
import NewJobManual from "./pages/jobs/NewJobManual";
import JobPost from "./pages/jobs/Template/JobPost";

//상세 보기 (선택 사항)
//import JobDetail from "./pages/jobs/Detail/JobDetail";

//소일거리 매칭 관련 페이지
import MatchingPage from "./pages/matching/MatchingPage";
import JobApplicationList from "./pages/applications/JobApplicationList";
import JobPostedList from "./pages/applications/JobPostedList";
import JobDetail from "./pages/jobs/JobDetail";

//관리자용 페이지
import AdminLogin from "./pages/admin/AdminLogin";
import AdminApproval from "./pages/admin/AdminApproval";

//알림페이지
import Notification from "./pages/notifications/Notification";

// === 안전 감싸기: import가 잘못됐으면 대체 UI + 콘솔 경고 ===
function safeElement(Comp, name) {
  const isReactFunction = typeof Comp === "function";
  const isReactForwardRef = Comp && typeof Comp === "object" && Comp.$$typeof;
  if (!isReactFunction && !isReactForwardRef) {
    console.error(
      `[Route element error] <${name}/> import가 올바르지 않아요. ` +
      `이 파일의 export/default 를 확인하세요. 현재 타입:`,
      Comp
    );
    return (
      <div className="min-h-[40vh] flex items-center justify-center">
        <div className="text-center text-sm text-red-600">
          <div className="font-semibold mb-1">{name} 로드 실패</div>
          <div>콘솔을 확인해 주세요 (default/named import 점검)</div>
        </div>
      </div>
    );
  }
  return <Comp />;
}

function AppRoutes() {
  const { pathname } = useLocation();

  // 하단바 가리고 싶은 페이지 추가
  const hideNav = ["/","/login", "/register", "/onboarding"].some((p) => pathname.startsWith(p));

  return (
    <>
      <Routes>
        <Route path="/" element={safeElement(Main, "Main")} />
        <Route path="/register" element={safeElement(RegisterFlow, "RegisterFlow")} />
        <Route path="/login" element={safeElement(Login, "Login")} />
        <Route path="/adminlogin" element={safeElement(AdminLogin, "AdminLogin")}/>
        <Route path="/approval" element={safeElement(AdminApproval, "AdminApproval")}/>

        {/* 온보딩 */}
        <Route path="/onboarding/nickname" element={safeElement(Nickname, "Nickname")} />
        <Route path="/onboarding/location" element={safeElement(Location, "Location")} />
        <Route path="/onboarding/time" element={safeElement(Time, "Time")} />
        <Route path="/onboarding/history" element={safeElement(JobCategorySelection, "JobCategorySelection")} />
        <Route path="/onboarding/capability" element={safeElement(Capability, "Capability")} />
        <Route path="/onboarding/summary" element={safeElement(OnboardingSummary, "OnboardingSummary")} />

        {/* 메인/마이페이지 */}
        <Route path="/main" element={safeElement(MainHome, "MainHome")} />
        <Route path="/mypage" element={safeElement(MyPage, "MyPage")} />

        {/* 음성 기반 */}
        <Route path="/jobs/from-voice/record" element={<VoiceRecording />} />
        <Route path="/jobs/from-voice/review" element={<JobPostTemplate />} />

        {/* 이미지 기반 */}
        <Route path="/jobs/from-image/upload" element={<ImageUpload />} />
        <Route path="/jobs/from-image/review" element={<JobPost />} />

        {/*📝 직접 등록*/}
        <Route path="/jobs/newjobmanual" element={<NewJobManual />} />

        {/* 소일거리 매칭 */}
        <Route path="/matchingpage" element={<MatchingPage/>}/>
        <Route path="/jobapplicationlist" element={<JobApplicationList/>}/>
        <Route path="/jobpostedlist" element={<JobPostedList/>}/>

        {/* 알림 */}
        <Route path="/notification" element={<Notification/>}/>

        {/* 상세 공고 페이지 (신규 및 기존 경로 모두 지원) */}
        <Route path="/jobs/:id" element={<JobDetail />} />
        <Route path="/jobdetail/:id" element={<JobDetail />} />

       
      </Routes>

      {!hideNav && safeElement(BottomNav, "BottomNav")}
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
