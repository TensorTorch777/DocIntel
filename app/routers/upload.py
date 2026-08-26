"""Multimodal upload, indexing, and chat-side media analysis."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies import get_ingestion_service, get_media_extractor
from app.models.schemas import MediaAnalyzeResponse, UploadResponse
from app.services.ingestion import IngestionService
from app.services.media import MediaExtractor
from app.utils.exceptions import DocIntelError, to_http_exception

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ingestion"])

MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB

ALLOWED_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".tif",
    ".tiff",
    ".bmp",
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".flac",
    ".webm",
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".m4v",
}


def _validate_upload(file: UploadFile) -> bytes:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file type. Upload a PDF, image (png/jpg/webp), "
                "audio voice note (wav/m4a/mp3/webm), or video (mp4/mov/webm)."
            ),
        )
    return suffix


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a PDF, image, audio, or video",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF, image, voice note, or video"),
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> UploadResponse:
    """Accept a document or media file, extract text, chunk, embed, and index."""
    _validate_upload(file)
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )

    try:
        return await ingestion.ingest_file(
            file.filename or "upload",
            content,
            content_type=file.content_type,
        )
    except DocIntelError as exc:
        raise to_http_exception(exc) from exc
    except Exception as exc:
        logger.exception("Upload failed for %s", file.filename)
        raise to_http_exception(DocIntelError(f"Ingestion failed: {exc}")) from exc


@router.post(
    "/media/analyze",
    response_model=MediaAnalyzeResponse,
    summary="Extract OCR or transcript from a chat attachment (not indexed)",
)
async def analyze_media(
    file: UploadFile = File(..., description="Image, voice note, or short video"),
    media: MediaExtractor = Depends(get_media_extractor),
) -> MediaAnalyzeResponse:
    """Transcribe or OCR a chat-side attachment without indexing a new document."""
    import tempfile

    _validate_upload(file)
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )

    suffix = Path(file.filename or "attach.bin").suffix or ".bin"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(content)
            tmp.flush()
            extracted = media.extract(
                Path(tmp.name),
                filename=file.filename or Path(tmp.name).name,
                content_type=file.content_type,
                file_bytes=content,
            )
        return MediaAnalyzeResponse(
            filename=file.filename or "attachment",
            modality=extracted.kind,
            text=extracted.full_text,
            page_count=extracted.page_count,
            duration_seconds=extracted.duration_seconds,
            transcript_available=extracted.transcript_available,
            ocr_available=extracted.ocr_available,
            engine=extracted.engine,
            notes=list(extracted.notes),
        )
    except DocIntelError as exc:
        raise to_http_exception(exc) from exc
    except Exception as exc:
        logger.exception("Media analyze failed for %s", file.filename)
        raise to_http_exception(DocIntelError(f"Media analysis failed: {exc}")) from exc
