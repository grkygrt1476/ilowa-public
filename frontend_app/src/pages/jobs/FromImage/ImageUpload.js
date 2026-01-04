import React, { useMemo, useState } from "react";
import { ChevronLeft, Image as ImageIcon, Camera } from "lucide-react";
import { useNavigate } from "react-router-dom";

import {
  AIAPI,
  MediaAPI,
  parseApiError,
  getStoredToken,
} from "../../../utils/apiClient";

export default function ImageUpload() {
  const nav = useNavigate();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [errMsg, setErrMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const accept = useMemo(() => "image/*", []);

  const handleBack = () => {
    if (window.history.length > 1) nav(-1);
    else nav("/");
  };

  const pickFromGallery = () => document.getElementById("imgFileInput")?.click();

  const onFileChange = (e) => {
    setErrMsg("");
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const pipeline = async () => {
    // 1) 업로드 -> 2) OCR -> 3) 헤더 의미 해석 -> 4) 검증 -> 5) 리뷰 이동
    const token = getStoredToken();
    if (!token) { setErrMsg("로그인이 필요합니다. 먼저 로그인해주세요."); return; }
    if (!file) { setErrMsg("이미지를 선택해주세요."); return; }

    setLoading(true);
    try {
      // 1) 이미지 업로드
      const uploadRes = await MediaAPI.uploadImages([file]);
      const uploadIds = uploadRes?.upload_ids || uploadRes?.ids;
      if (!uploadIds || !uploadIds.length) throw new Error("업로드 식별자를 받지 못했어요.");

      // 2) OCR 파싱
      const ocrRes = await AIAPI.parseOcr({ upload_ids: uploadIds });
      const rawText = ocrRes?.raw_text || "";
      const cells = ocrRes?.cells || [];

      // 3) 필드 매핑
      const mappingRes = await AIAPI.mapHeaders({ raw_text: rawText, cells });
      const mappedFields = mappingRes?.mapped_fields || {};
      const confidence = mappingRes?.confidence;

      // 4) 매핑 검증
      const validation = await AIAPI.validateMapping({ mapped_fields: mappedFields });
      const validationResult = validation?.validation_result;

      // 5) 템플릿 페이지(리뷰)로 이동
      nav("/jobs/from-image/review", {
        state: {
          mapped_fields: mappedFields,
          confidence,
          validation_result: validationResult,
          raw_text: rawText,
        },
      });
    } catch (e) {
      setErrMsg(parseApiError(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <input id="imgFileInput" type="file" accept={accept} className="hidden" onChange={onFileChange} />
      <header className="px-6 py-4 flex items-center border-b">
        <button onClick={handleBack} className="p-2"><ChevronLeft className="w-6 h-6" /></button>
        <h1 className="text-lg font-bold ml-4">이미지 업로드</h1>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6">
        {errMsg && (
          <div className="w-full max-w-md bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 mb-4 whitespace-pre-line">
            {errMsg}
          </div>
        )}

        <h2 className="text-3xl font-bold mb-4 text-center">사진을 선택하거나<br/>촬영해주세요</h2>
        <p className="text-gray-600 text-lg mb-12 text-center">공고 내용이 담긴 이미지를 올려주세요</p>

        <div className="w-full max-w-md space-y-4">
          {/* 카메라 촬영: 실제 카메라 API 연결 시 교체 */}
          <button
            disabled={loading}
            onClick={pickFromGallery}
            className="w-full bg-[#F4BA4D] hover:bg-[#E5AB3D] p-6 rounded-2xl shadow-lg transition-all disabled:opacity-60"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-white rounded-full flex items-center justify-center">
                <Camera className="w-7 h-7 text-[#F4BA4D]" />
              </div>
              <div className="flex-1 text-left">
                <h3 className="text-xl font-bold text-white">사진 촬영 / 선택</h3>
              </div>
            </div>
          </button>

          <button
            disabled={loading}
            onClick={pickFromGallery}
            className="w-full bg-white hover:bg-gray-50 p-6 rounded-2xl shadow-lg border-2 border-[#F4BA4D] transition-all disabled:opacity-60"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-[#FEF3E2] rounded-full flex items-center justify-center">
                <ImageIcon className="w-7 h-7 text-[#F4BA4D]" />
              </div>
              <div className="flex-1 text-left">
                <h3 className="text-xl font-bold text-gray-800">갤러리에서 선택</h3>
              </div>
            </div>
          </button>
        </div>

        {preview && (
          <div className="w-full max-w-md mt-8">
            <div className="bg-gray-100 rounded-xl p-4 mb-4">
              <div className="aspect-video bg-gray-200 rounded-lg flex items-center justify-center overflow-hidden">
                <img src={preview} alt="preview" className="object-contain max-h-72" />
              </div>
            </div>
            <button
              disabled={loading}
              onClick={pipeline}
              className="w-full bg-[#F4BA4D] text-white font-bold text-xl py-5 rounded-xl hover:bg-[#E5AB3D] transition disabled:opacity-60"
            >
              {loading ? "처리 중..." : "다음"}
            </button>
          </div>
        )}

        <p className="text-gray-500 text-sm mt-8 text-center">💡 이미지 속 텍스트를 자동으로 인식해요</p>
      </main>
    </div>
  );
}