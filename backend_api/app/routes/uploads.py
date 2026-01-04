"""Simple media upload endpoints for image and audio files."""

from __future__ import annotations

import os
import pathlib
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session

from backend_api.app.core.security import get_current_user_id
from backend_api.app.db.database import get_db
from backend_api.app.db.models import MediaUpload
from backend_api.app.schemas.jobs import UploadResponse


try:  # Optional import guard for PDF conversion
    import fitz  # type: ignore
except Exception:  # pragma: no cover - import failure handled at runtime
    fitz = None


UPLOAD_DIR = pathlib.Path(os.getenv("MEDIA_UPLOAD_DIR", "backend_api/app/storage"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


router = APIRouter(prefix="/uploads", tags=["Uploads"])


def _convert_pdf_to_images(pdf_path: pathlib.Path) -> list[pathlib.Path]:
    """Convert the first page of a PDF into a JPEG image for preview purposes."""

    if fitz is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF 변환 라이브러리가 설치되지 않았습니다. (PyMuPDF)",
        )

    images: list[pathlib.Path] = []
    with fitz.open(pdf_path) as doc:  # type: ignore[attr-defined]
        if doc.page_count == 0:
            return images

        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # type: ignore[attr-defined]
        output = pdf_path.with_name(f"{pdf_path.stem}_page1.jpg")
        pix.save(output)  # type: ignore[attr-defined]
        images.append(output)

    return images


def _save_file(file: UploadFile, media_type: str, db: Session) -> tuple[UUID, str]:
    upload_id = uuid4()
    suffix = pathlib.Path(file.filename or "").suffix or (".jpg" if media_type == "image" else ".dat")
    filename = f"{upload_id}{suffix}"
    destination = UPLOAD_DIR / filename

    with destination.open("wb") as buffer:
        contents = file.file.read()
        if not contents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="빈 파일은 업로드할 수 없습니다.")
        buffer.write(contents)

    raw_url = f"/media/{filename}"
    extra: dict[str, list[str] | str] = {"raw_path": str(destination), "raw_url": raw_url}

    converted_urls: list[str] = []
    if suffix.lower() == ".pdf":
        converted_paths = _convert_pdf_to_images(destination)
        if converted_paths:
            converted_urls = [f"/media/{path.name}" for path in converted_paths]
            extra["converted_files"] = [str(path) for path in converted_paths]
            extra["converted_urls"] = converted_urls

    record = MediaUpload(
        id=upload_id,
        media_type=media_type,
        original_name=file.filename or filename,
        file_path=str(destination),
        extra=extra,
    )
    db.add(record)
    primary_url = converted_urls[0] if converted_urls else raw_url
    return upload_id, primary_url


@router.post("/images", response_model=UploadResponse)
async def upload_images(
    files: List[UploadFile] = File(...),
    current_user_id=Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    del current_user_id  # 토큰 확인용으로만 사용
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업로드할 파일이 없습니다.")

    upload_ids: list[UUID] = []
    urls: list[str] = []
    for file in files:
        upload_id, preview_url = _save_file(file, "image", db)
        upload_ids.append(upload_id)
        urls.append(preview_url)

    db.commit()
    return UploadResponse(upload_ids=upload_ids, urls=urls)


@router.post("/audio", response_model=UploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    current_user_id=Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    del current_user_id
    upload_id, preview_url = _save_file(file, "audio", db)
    db.commit()
    return UploadResponse(upload_ids=[upload_id], urls=[preview_url])
