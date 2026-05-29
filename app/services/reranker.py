"""Cross-encoder reranking for precision retrieval."""

import logging
from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.config import Settings
from app.services.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)

_FALLBACK_MODELS = (
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
)


@lru_cache(maxsize=4)
def _load_reranker(model_name: str) -> CrossEncoder:
    logger.info("Loading reranker model: %s", model_name)
    return CrossEncoder(model_name)


def _init_reranker(primary: str) -> CrossEncoder | None:
    """Load primary reranker with fallbacks."""
    candidates = [primary, *_FALLBACK_MODELS]
    seen: set[str] = set()
    for name in candidates:
        if name in seen:
            continue
        seen.add(name)
        try:
            return _load_reranker(name)
        except Exception as exc:
            logger.warning("Failed to load reranker %s: %s", name, exc)
    return None


class RerankerService:
    """Rerank retrieved chunks with a cross-encoder on the FULL user query."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = (
            _init_reranker(settings.reranker_model) if settings.reranker_enabled else None
        )

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """Score query-chunk pairs; sort by rerank score descending."""
        if not chunks:
            return []

        k = top_k or self._settings.retrieval_top_k

        if not self._settings.reranker_enabled or self._model is None:
            return sorted(chunks, key=lambda c: c.score, reverse=True)[:k]

        pairs = [[query, chunk.text] for chunk in chunks]
        rerank_scores = self._model.predict(pairs, show_progress_bar=False)

        scored: list[tuple[RetrievedChunk, float]] = []
        for chunk, rerank_score in zip(chunks, rerank_scores, strict=True):
            meta = dict(chunk.metadata)
            if "vector_score" not in meta:
                meta["vector_score"] = float(meta.get("vector_score", 0.0))
            meta["rerank_score"] = float(rerank_score)
            scored.append(
                (
                    RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        text=chunk.text,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        score=float(rerank_score),
                        metadata=meta,
                    ),
                    float(rerank_score),
                )
            )

        scored.sort(key=lambda item: item[1], reverse=True)
        result = [item[0] for item in scored[:k]]
        logger.info(
            "Reranked %d candidates -> top %d (best=%.3f)",
            len(chunks),
            len(result),
            result[0].score if result else 0.0,
        )
        return result
