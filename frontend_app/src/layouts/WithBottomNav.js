import React from "react";
import { Outlet } from "react-router-dom";
import BottomNav from "../components/BottomNav";

export default function WithBottomNav() {
  return (
    <div className="min-h-screen bg-white">
      {/* 컨텐츠가 바텀내비에 가려지지 않도록 패딩 */}
      <div className="pb-[100px]">
        <Outlet />
      </div>
      <BottomNav />
    </div>
  );
}