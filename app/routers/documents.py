"""Document metadata endpoints."""

import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_vector_store
from app.models.schemas import DocumentInfo
from app.services.vector_store import VectorStoreService
from app.utils.exceptions import DocumentNotFoundError, to_http_exception

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get(
    "/{document_id}",
    response_model=DocumentInfo,
    summary="Get indexed document metadata",
)
async def get_document(
    document_id: str,
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> DocumentInfo:
    """Return metadata for an indexed document."""
    info = vector_store.get_document_info(document_id)
    if info is None:
        raise to_http_exception(
            DocumentNotFoundError(f"Document '{document_id}' not found")
        )
    return DocumentInfo(**info)
