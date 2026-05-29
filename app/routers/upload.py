"""PDF upload and indexing endpoint."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies import get_ingestion_service
from app.models.schemas import UploadResponse
from app.services.ingestion import IngestionService
from app.utils.exceptions import DocIntelError, to_http_exception

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Ingestion"])

MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a PDF document",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF engineering report"),
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> UploadResponse:
    """
    Accept a PDF file, extract text, chunk, embed, and persist in ChromaDB.

    Returns a ``document_id`` for use with ``/chat`` and other endpoints.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

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
        return await ingestion.ingest_pdf(file.filename, content)
    except DocIntelError as exc:
        raise to_http_exception(exc) from exc
    except Exception as exc:
        logger.exception("Upload failed for %s", file.filename)
        raise to_http_exception(DocIntelError(f"Ingestion failed: {exc}")) from exc
