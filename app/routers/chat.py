"""Streaming chat and RAG endpoints."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_rag_service
from app.models.schemas import (
    AnomalyRequest,
    AnomalyResponse,
    ChatRequest,
    SummarizeRequest,
    SummarizeResponse,
)
from app.services.rag import RAGService
from app.utils.exceptions import DocIntelError, to_http_exception
from app.utils.sse import rag_event_generator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["RAG"])


@router.post(
    "/chat",
    summary="Stream RAG response via Server-Sent Events",
    response_class=StreamingResponse,
)
async def chat(
    request: ChatRequest,
    rag: RAGService = Depends(get_rag_service),
) -> StreamingResponse:
    """
    Retrieve, rerank, generate, and verify with full source transparency.

    SSE events:
    - ``sources`` — retrieved chunks with scores (before generation)
    - ``token`` — incremental text chunk
    - ``done`` — includes sources + verification result
    - ``error`` — failure message
    """
    try:
        event_stream = rag.stream_chat_events(
            document_id=request.document_id,
            query=request.query,
            task=request.task,
            top_k=request.top_k,
            debug=request.debug,
        )

        return StreamingResponse(
            rag_event_generator(event_stream),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except DocIntelError as exc:
        raise to_http_exception(exc) from exc
    except Exception as exc:
        logger.exception("Chat stream failed")
        raise to_http_exception(DocIntelError(f"Chat failed: {exc}")) from exc


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    summary="Generate structured document summary (non-streaming)",
)
async def summarize(
    request: SummarizeRequest,
    rag: RAGService = Depends(get_rag_service),
) -> SummarizeResponse:
    """Produce a structured engineering report summary."""
    try:
        return await rag.summarize(request.document_id, focus=request.focus)
    except DocIntelError as exc:
        raise to_http_exception(exc) from exc
    except Exception as exc:
        logger.exception("Summarization failed")
        raise to_http_exception(DocIntelError(f"Summarization failed: {exc}")) from exc


@router.post(
    "/anomaly",
    response_model=AnomalyResponse,
    summary="Scan document for engineering anomalies (non-streaming)",
)
async def detect_anomalies(
    request: AnomalyRequest,
    rag: RAGService = Depends(get_rag_service),
) -> AnomalyResponse:
    """Flag inconsistent parameters and out-of-bounds metrics."""
    try:
        return await rag.detect_anomalies(request.document_id, parameters=request.parameters)
    except DocIntelError as exc:
        raise to_http_exception(exc) from exc
    except Exception as exc:
        logger.exception("Anomaly detection failed")
        raise to_http_exception(DocIntelError(f"Anomaly detection failed: {exc}")) from exc
