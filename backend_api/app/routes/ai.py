"""AI endpoints that proxy calls to the ai_modeling orchestration layer."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from ai_modeling.schemas.recommendation import RecommendationRequest

from backend_api.app.core.security import get_current_user_id
from backend_api.app.db.database import get_db
from backend_api.app.db.models import MediaUpload
from backend_api.app.schemas.jobs import (
    AsrParseRequest,
    MappingRequest,
    MappingResponse,
    MappingValidateRequest,
    MappingValidateResponse,
    OcrParseRequest,
    OcrParseResponse,
    VoicePostRequest,
    VoicePostResponse,
)
from backend_api.app.services.ai_pipeline import get_pipeline
from backend_api.app.services.google_geocoder import GoogleGeocoder


class RecommendationPayload(RecommendationRequest):
    """Extends the ai_modeling schema with optional prior recommendations."""

    previous_recommendations: Optional[List[Dict[str, Any]]] = None


router = APIRouter(tags=["AI"], dependencies=[Depends(get_current_user_id)])
logger = logging.getLogger(__name__)
_GOOGLE_GEOCODER: Optional[GoogleGeocoder] = None
_GOOGLE_GEOCODER_DISABLED = False
_GOOGLE_GEOCODER_CACHE = Path(
    os.getenv("AI_ROUTES_GOOGLE_GEOCODER_CACHE", ".google_geocode_cache_ai.json")
)


def _fetch_uploads(db: Session, ids: List[UUID]) -> List[MediaUpload]:
    uploads = []
    for upload_id in ids:
        upload = db.get(MediaUpload, upload_id)
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"업로드 {upload_id}을(를) 찾을 수 없습니다.",
            )
        uploads.append(upload)
    return uploads


def _read_upload(upload: MediaUpload) -> tuple[bytes, Path]:
    candidate = upload.extra.get("raw_path") or upload.file_path
    path = Path(candidate)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"업로드 파일을 찾을 수 없습니다: {upload.id}",
        )
    return path.read_bytes(), path


def _post_to_cells(post: Dict[str, Any]) -> List[Dict[str, str]]:
    cells: List[Dict[str, str]] = []
    for idx, (key, value) in enumerate(post.items()):
        if isinstance(value, (str, int, float)) and str(value).strip():
            cells.append({"row": idx, "col": 0, "text": f"{key}: {value}"})
    return cells


def _combine_text(raw_segments: List[str], fallback: str) -> str:
    text = "\n\n".join([segment for segment in raw_segments if segment]).strip()
    return text or fallback


def _append_text(base: Optional[str], addition: Optional[str], max_length: int = 4000) -> str:
    base_text = (base or "").strip()
    extra = (addition or "").strip()
    if base_text and extra:
        combined = f"{base_text}\n{extra}"
    else:
        combined = extra or base_text
    if max_length and len(combined) > max_length:
        return combined[-max_length:]
    return combined


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    if isinstance(value, (int, float)):
        return value != 0
    return True


def _merge_structured_posts(current: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    if not current:
        return dict(incoming)
    merged = dict(current)
    if not incoming:
        return merged

    for key, value in incoming.items():
        if key == "confidence" and isinstance(value, dict):
            existing_conf = dict(merged.get("confidence") or {})
            existing_conf.update({k: v for k, v in value.items() if v is not None})
            merged["confidence"] = existing_conf
            continue
        if key == "raw_text":
            merged["raw_text"] = _append_text(merged.get("raw_text"), value)
            continue
        if not _has_value(merged.get(key)) and _has_value(value):
            merged[key] = value

    return merged


def _get_google_geocoder() -> Optional[GoogleGeocoder]:
    global _GOOGLE_GEOCODER, _GOOGLE_GEOCODER_DISABLED
    if _GOOGLE_GEOCODER_DISABLED:
        return None
    if _GOOGLE_GEOCODER is None:
        try:
            _GOOGLE_GEOCODER = GoogleGeocoder(cache_path=_GOOGLE_GEOCODER_CACHE)
            logger.info(
                "Google geocoder enabled for AI routes with cache %s",
                _GOOGLE_GEOCODER_CACHE,
            )
        except Exception as exc:
            _GOOGLE_GEOCODER_DISABLED = True
            logger.warning("Google geocoder unavailable for AI routes: %s", exc)
            return None
    return _GOOGLE_GEOCODER


def _geocode_with_client(google: GoogleGeocoder, query: str) -> Optional[tuple[float, float, Optional[str]]]:
    text = (query or "").strip()
    if not text:
        return None
    try:
        result = google.geocode(text, return_details=True)
    except Exception as exc:
        logger.warning("Google geocode failed for '%s': %s", text, exc)
        return None
    if not result:
        return None

    if isinstance(result, tuple) and len(result) == 3:
        lat, lng, formatted = result
        return lat, lng, formatted
    if isinstance(result, tuple) and len(result) == 2:
        lat, lng = result
        return lat, lng, None
    return None


def _address_context(post: Dict[str, Any]) -> Dict[str, str]:
    context: Dict[str, str] = {}
    for key in ("region", "place", "location", "description", "raw_text"):
        value = post.get(key)
        if isinstance(value, str) and value.strip():
            context[key] = value.strip()[:400]
    return context


def _maybe_refine_address(orchestrator, post_state: Dict[str, Any]) -> None:
    google = _get_google_geocoder()
    if not google or not post_state:
        return

    candidates = []
    for key in ("address", "place", "location", "region"):
        value = post_state.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())
    if not candidates:
        return

    geocode_result: Optional[tuple[float, float, Optional[str]]] = None
    chosen_query: Optional[str] = None

    for query in candidates:
        geocode_result = _geocode_with_client(google, query)
        if geocode_result:
            chosen_query = query
            break

    if not geocode_result and orchestrator:
        context = _address_context(post_state)
        rewritten = orchestrator.normalize_address(candidates[0], context=context)
        if rewritten and rewritten.strip() and rewritten.strip() not in candidates:
            chosen_query = rewritten.strip()
            geocode_result = _geocode_with_client(google, chosen_query)

    if not geocode_result:
        return

    lat, lng, formatted = geocode_result
    if lat is not None:
        post_state["lat"] = lat
    if lng is not None:
        post_state["lng"] = lng
    if formatted:
        post_state["address"] = formatted
    elif chosen_query and chosen_query != post_state.get("address"):
        post_state["address"] = chosen_query


@router.post("/recommend", response_model=Dict[str, Any])
def recommend_jobs(
    payload: RecommendationPayload,
    provider: Optional[str] = Query(
        default=None,
        description="사용할 AI Provider (예: naver, local)",
    ),
):
    orchestrator = get_pipeline(provider)
    result = orchestrator.recommend(
        user_profile=payload.user_profile.dict(),
        intent=payload.intent or "",
        previous_recommendations=payload.previous_recommendations or [],
    )
    result["provider"] = orchestrator.provider_name
    return result


@router.post("/ocr/parse", response_model=OcrParseResponse)
def parse_ocr(
    payload: OcrParseRequest,
    provider: Optional[str] = Query(default=None, description="AI Provider override"),
    db: Session = Depends(get_db),
):
    uploads = _fetch_uploads(db, payload.upload_ids)
    if not uploads:
        raise HTTPException(status_code=400, detail="이미지를 먼저 업로드해주세요.")

    orchestrator = get_pipeline(provider)
    raw_segments: List[str] = []
    cells: List[Dict[str, str]] = []

    for upload in uploads:
        content, _ = _read_upload(upload)
        try:
            result = orchestrator.create_post_from_image_bytes(content)
        except HTTPException:
            raise
        except ValueError as exc:
            logger.warning("OCR pipeline returned invalid response for %s: %s", upload.id, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OCR 결과를 처리하는 중 오류가 발생했습니다: {exc}",
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected OCR failure for %s", upload.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="이미지에서 텍스트를 추출하는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
            ) from exc

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "이미지에서 텍스트를 추출하지 못했습니다."),
            )
        post = result.get("post", {})
        raw_segments.append(
            (post.get("raw_text") or post.get("description") or "").strip()
        )
        cells.extend(_post_to_cells(post))

    return OcrParseResponse(
        raw_text=_combine_text(raw_segments, "텍스트 추출 결과가 비어 있습니다."),
        cells=cells,
    )


@router.post("/asr/parse", response_model=OcrParseResponse)
def parse_asr(
    payload: AsrParseRequest,
    provider: Optional[str] = Query(default=None, description="AI Provider override"),
    db: Session = Depends(get_db),
):
    uploads = _fetch_uploads(db, payload.upload_ids)
    if not uploads:
        raise HTTPException(status_code=400, detail="음성 파일을 업로드해주세요.")

    orchestrator = get_pipeline(provider)
    transcripts: List[str] = []
    for upload in uploads:
        _, path = _read_upload(upload)
        try:
            stt = orchestrator.transcribe_audio_file(str(path))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"음성 인식 실패: {exc}",
            ) from exc

        transcripts.append((stt or {}).get("text", "").strip())

    return OcrParseResponse(
        raw_text=_combine_text(transcripts, "음성에서 텍스트를 추출하지 못했습니다."),
        cells=[],
    )


@router.post("/voice/post", response_model=VoicePostResponse)
def create_post_from_voice(
    payload: VoicePostRequest,
    provider: Optional[str] = Query(default=None, description="AI Provider override"),
    db: Session = Depends(get_db),
):
    orchestrator = get_pipeline(provider)
    existing_post = payload.existing_post or {}
    has_existing = bool(existing_post)
    post_state: Dict[str, Any] = dict(existing_post) if has_existing else {}
    transcript_parts: List[str] = []

    if payload.upload_id:
        uploads = _fetch_uploads(db, [payload.upload_id])
        upload = uploads[0]
        content, _ = _read_upload(upload)
        try:
            voice_result = orchestrator.create_post_from_voice_bytes(content)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"음성 처리에 실패했습니다: {exc}",
            ) from exc

        if not voice_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=voice_result.get("message", "음성에서 공고를 추출하지 못했습니다."),
            )

        structured_post = voice_result.get("post") or {}
        if not structured_post:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="추출된 공고가 비어 있습니다.",
            )

        if has_existing:
            post_state = _merge_structured_posts(post_state, structured_post)
        else:
            post_state = structured_post

        transcript_value = (voice_result.get("transcript") or "").strip()
        if transcript_value:
            transcript_parts.append(transcript_value)
    else:
        manual = (payload.clarification_text or "").strip()
        if not manual:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="음성 파일 또는 추가 설명이 필요합니다.",
            )
        if not has_existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="기존 초안이 없어 추가 설명을 반영할 수 없습니다.",
            )
        post_state = dict(existing_post)

    manual_text = (payload.clarification_text or "").strip()
    if manual_text:
        transcript_parts.append(manual_text)

    transcript_text = "\n".join([segment for segment in transcript_parts if segment]).strip()

    if transcript_text:
        if has_existing:
            post_state = orchestrator.merge_post_with_text(post_state, transcript_text)
        else:
            post_state["raw_text"] = _append_text(post_state.get("raw_text"), transcript_text)

    if not post_state:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="생성된 공고 데이터가 없습니다.",
        )

    _maybe_refine_address(orchestrator, post_state)

    validation = orchestrator.validate_post(post_state)
    missing = validation.get("missing_fields") or validation.get("missing") or []
    questions = validation.get("questions") or []
    needs_clarification = validation.get("needs_clarification")
    if needs_clarification is None:
        needs_clarification = bool(missing)

    return VoicePostResponse(
        post=post_state,
        transcript=transcript_text or None,
        missing_fields=missing,
        questions=questions,
        needs_clarification=needs_clarification,
        provider=orchestrator.provider_name,
    )


@router.post("/vlm/headers", response_model=MappingResponse)
def map_headers(
    payload: MappingRequest,
    provider: Optional[str] = Query(default=None, description="AI Provider override"),
):
    orchestrator = get_pipeline(provider)
    text = (payload.raw_text or "").strip()
    if not text and payload.cells:
        text = "\n".join(str(cell.get("text", "")) for cell in payload.cells).strip()
    if not text:
        raise HTTPException(status_code=400, detail="매핑할 텍스트가 필요합니다.")

    try:
        result = orchestrator.create_post_from_text(text)
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning("Header mapping failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 응답 처리 중 오류가 발생했습니다: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected header mapping failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="필드 매핑 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
        ) from exc
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "필드 추출에 실패했습니다."),
        )
    post = result.get("post", {})
    confidence_map = post.get("confidence") or {}
    scores = [
        float(v)
        for v in confidence_map.values()
        if isinstance(v, (float, int))
    ]
    avg_conf = sum(scores) / len(scores) if scores else 0.85
    return MappingResponse(mapped_fields=post, confidence=round(avg_conf, 2))


@router.post("/mapping/validate", response_model=MappingValidateResponse)
def validate_mapping(
    payload: MappingValidateRequest,
    provider: Optional[str] = Query(default=None, description="AI Provider override"),
):
    orchestrator = get_pipeline(provider)
    post = payload.mapped_fields or {}
    validation = orchestrator.validate_post(post)

    missing = validation.get("missing_fields", [])
    result = {
        "missing": missing,
        "questions": validation.get("questions", []),
        "needs_clarification": validation.get("needs_clarification", False),
        "ready": not validation.get("needs_clarification", False),
    }
    return MappingValidateResponse(validation_result=result)
