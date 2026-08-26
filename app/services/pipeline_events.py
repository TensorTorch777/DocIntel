"""Pipeline stage identifiers and SSE event payloads for live RAG timeline."""

from __future__ import annotations

from enum import Enum
from typing import Any

PIPELINE_STAGES: tuple[tuple[str, str], ...] = (
    ("understanding_query", "Understanding Query"),
    ("moe_routing", "MoE Expert Routing"),
    ("query_expansion", "Query Expansion"),
    ("vector_retrieval", "Vector Retrieval"),
    ("bm25_retrieval", "BM25 Retrieval"),
    ("rrf_fusion", "RRF Fusion"),
    ("cross_encoder_reranking", "Cross-Encoder Reranking"),
    ("definition_resolution", "Definition Resolution"),
    ("evidence_sufficiency", "Evidence Sufficiency Check"),
    ("answer_generation", "Answer Generation"),
    ("verification", "Verification"),
)

STAGE_LABELS: dict[str, str] = dict(PIPELINE_STAGES)


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"


def pipeline_event(
    stage: str,
    status: str,
    *,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a pipeline SSE payload."""
    return {
        "stage": stage,
        "label": STAGE_LABELS.get(stage, stage.replace("_", " ").title()),
        "status": status.value if isinstance(status, StageStatus) else status,
        "detail": detail or {},
    }


def expansion_terms(core_query: str, retrieval_query: str) -> list[str]:
    """Terms added during query expansion (for timeline detail)."""
    import re

    stop = {
        "what", "how", "does", "the", "and", "for", "with", "from", "that", "this",
        "are", "is", "of", "in", "to", "a", "an", "on", "or", "be", "by", "at",
    }
    core = {t for t in re.findall(r"[A-Za-z0-9#_.-]+", core_query.lower()) if t not in stop}
    added: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9#_.-]+", retrieval_query):
        key = token.lower()
        if key in core or key in stop or len(key) < 2:
            continue
        if key not in seen:
            seen.add(key)
            added.append(token)
    return added[:12]


def top_rerank_scores(chunks: list, limit: int = 3) -> list[dict[str, float | int]]:
    """Top rerank scores for timeline display."""
    scored = []
    for chunk in chunks:
        score = float(chunk.metadata.get("rerank_score", chunk.score))
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    result: list[dict[str, float | int]] = []
    for score, chunk in scored[:limit]:
        result.append(
            {
                "score": round(score, 3),
                "page": chunk.page_number or 0,
            }
        )
    return result
