"""Server-Sent Events (SSE) streaming helpers."""

import json
from collections.abc import AsyncIterator
from typing import Any


def format_sse_event(event: str, data: dict[str, Any]) -> str:
    """Format a single SSE frame."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


async def rag_event_generator(
    event_stream: AsyncIterator[tuple[str, dict[str, Any]]],
) -> AsyncIterator[str]:
    """Convert RAG (event, data) tuples into SSE frames."""
    try:
        async for event, data in event_stream:
            yield format_sse_event(event, data)
    except Exception as exc:
        yield format_sse_event("error", {"message": str(exc)})


async def sse_event_generator(
    token_stream: AsyncIterator[str],
    *,
    done_payload: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """
    Wrap an async token stream into SSE frames.

    Emits ``token`` events for each chunk, then a ``done`` event.
    """
    try:
        async for token in token_stream:
            yield format_sse_event("token", {"content": token})

        yield format_sse_event("done", done_payload or {"status": "complete"})
    except Exception as exc:
        yield format_sse_event("error", {"message": str(exc)})
