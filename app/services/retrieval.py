"""Hybrid retrieval: query rewrite → vector + BM25 → RRF → entity boost → rerank."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings
from benchmark.pipeline import PipelineConfig
from app.models.schemas import EvidenceCoverage, EvidenceSufficiency, RetrievedSource
from app.services.bm25_store import BM25Store
from app.services.definitional_boost import apply_definitional_boost
from app.services.embedding import EmbeddingService
from app.services.entity_matcher import apply_entity_boost, extract_entities
from app.services.evidence_sufficiency import assess_sufficiency
from app.services.query_rewriter import expand_query
from app.services.register_definition_resolver import (
    extract_register_entities,
    merge_pinned_with_reranked,
    pin_definition_chunks,
    resolve_authoritative_definitions,
    sort_definition_first,
)
from app.services.reranker import RerankerService
from app.services.vector_store import RetrievedChunk, VectorStoreService

logger = logging.getLogger(__name__)

RRF_K = 60


@dataclass
class RetrievalDebugInfo:
    """Debug metadata for retrieval evaluation."""

    original_query: str
    core_query: str
    retrieval_query: str
    vector_candidates: list[RetrievedSource] = field(default_factory=list)
    bm25_candidates: list[RetrievedSource] = field(default_factory=list)
    merged_candidates: list[RetrievedSource] = field(default_factory=list)
    selected_chunks: list[RetrievedSource] = field(default_factory=list)
    rejected_chunks: list[RetrievedSource] = field(default_factory=list)
    entities_detected: list[str] = field(default_factory=list)
    retrieval_confidence: str = "medium"
    evidence_coverage: dict[str, Any] = field(default_factory=dict)
    pinned_chunks: list[RetrievedSource] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_query": self.original_query,
            "core_query": self.core_query,
            "retrieval_query": self.retrieval_query,
            "entities_detected": self.entities_detected,
            "retrieval_confidence": self.retrieval_confidence,
            "evidence_coverage": self.evidence_coverage,
            "pinned_chunks": [s.model_dump() for s in self.pinned_chunks],
            "vector_candidates": [s.model_dump() for s in self.vector_candidates],
            "bm25_candidates": [s.model_dump() for s in self.bm25_candidates],
            "merged_candidates": [s.model_dump() for s in self.merged_candidates],
            "selected_chunks": [s.model_dump() for s in self.selected_chunks],
            "rejected_chunks": [s.model_dump() for s in self.rejected_chunks],
        }


@dataclass
class RetrievalTimings:
    """Stage latencies in milliseconds."""

    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0


@dataclass
class RetrievalResult:
    """Final retrieval output."""

    chunks: list[RetrievedChunk]
    context: str
    sources: list[RetrievedSource]
    debug: RetrievalDebugInfo
    sufficiency: EvidenceSufficiency
    timings: RetrievalTimings = field(default_factory=RetrievalTimings)


def _rrf_merge(
    *ranked_lists: list[RetrievedChunk],
    k: int = RRF_K,
) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion across multiple ranked chunk lists."""
    scores: dict[str, float] = {}
    chunk_map: dict[str, RetrievedChunk] = {}

    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked):
            cid = chunk.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            if cid not in chunk_map:
                chunk_map[cid] = chunk
            else:
                # Merge metadata from both retrieval paths
                merged_meta = dict(chunk_map[cid].metadata)
                merged_meta.update(chunk.metadata)
                chunk_map[cid] = RetrievedChunk(
                    chunk_id=cid,
                    text=chunk_map[cid].text,
                    page_number=chunk_map[cid].page_number or chunk.page_number,
                    chunk_index=chunk_map[cid].chunk_index,
                    score=chunk_map[cid].score,
                    metadata=merged_meta,
                )

    sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    merged: list[RetrievedChunk] = []
    for cid in sorted_ids:
        chunk = chunk_map[cid]
        meta = dict(chunk.metadata)
        meta["rrf_score"] = scores[cid]
        merged.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                score=scores[cid],
                metadata=meta,
            )
        )
    return merged


def _chunk_to_debug_source(
    chunk: RetrievedChunk,
    index: int,
    *,
    selected: bool = False,
) -> RetrievedSource:
    excerpt = chunk.text[:280] + ("…" if len(chunk.text) > 280 else "")
    return RetrievedSource(
        source_index=index,
        chunk_id=chunk.chunk_id,
        page_number=chunk.page_number,
        vector_score=float(chunk.metadata.get("vector_score", 0.0)),
        rerank_score=float(chunk.metadata.get("rerank_score", chunk.score)),
        bm25_score=float(chunk.metadata.get("bm25_score", 0.0)) or None,
        rrf_score=float(chunk.metadata.get("rrf_score", 0.0)) or None,
        entity_hits=int(chunk.metadata.get("entity_hits", 0)),
        excerpt=excerpt,
        selected=selected,
    )


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Format chunks with stable source IDs; definition chunks listed first."""
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        page = f"Page {chunk.page_number}" if chunk.page_number else "Page unknown"
        vector_score = chunk.metadata.get("vector_score", 0.0)
        rerank_score = chunk.metadata.get("rerank_score", chunk.score)
        tags: list[str] = []
        if chunk.metadata.get("pinned_definition"):
            entity = chunk.metadata.get("definition_entity", "")
            tags.append(f"AUTHORITATIVE DEFINITION{': ' + entity if entity else ''}")
        elif chunk.metadata.get("chunk_tier") == 1:
            tags.append("DEFINITION")
        tag_str = f" | {' | '.join(tags)}" if tags else ""
        parts.append(
            f"[Source {i} | id={chunk.chunk_id} | {page} | "
            f"vector={vector_score:.3f} | rerank={rerank_score:.3f}{tag_str}]\n"
            f"{chunk.text}"
        )
    return "\n\n---\n\n".join(parts)


class RetrievalService:
    """Orchestrate hybrid retrieval pipeline."""

    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreService,
        bm25_store: BM25Store,
        reranker_service: RerankerService,
        llm_service=None,
    ) -> None:
        self._settings = settings
        self._embeddings = embedding_service
        self._vector_store = vector_store
        self._bm25 = bm25_store
        self._reranker = reranker_service
        self._llm = llm_service

    async def retrieve(
        self,
        document_id: str,
        user_query: str,
        top_k: int | None = None,
        pipeline: PipelineConfig | None = None,
    ) -> RetrievalResult:
        """
        Full pipeline:
        definition resolver → pinned chunks + vector + BM25 → RRF → boost → rerank → pin merge
        """
        t0 = time.perf_counter()
        timings = RetrievalTimings()

        cfg = pipeline
        use_hybrid = cfg.hybrid if cfg else self._settings.hybrid_retrieval_enabled
        use_rerank = cfg.rerank if cfg else self._settings.reranker_enabled
        use_def_resolver = (
            cfg.definition_resolver if cfg else self._settings.enable_register_definition_resolver
        )
        use_entity_boost = cfg.entity_boost if cfg else True
        use_def_boost = cfg.definitional_boost if cfg else True

        final_k = top_k or self._settings.retrieval_top_k
        candidate_k = max(final_k, self._settings.retrieval_candidate_k)

        original_query, core_query, retrieval_query = await expand_query(
            user_query,
            llm_service=self._llm,
            use_llm=self._settings.enable_query_rewrite_llm,
        )

        entities = extract_entities(core_query)
        register_entities = extract_register_entities(user_query)
        entity_list = list(
            dict.fromkeys(
                list(register_entities)
                + list(entities.registers)
                + list(entities.exceptions)
                + list(entities.flags)
            )
        )

        # 1. Register definition resolver (scan full BM25 corpus)
        pinned: list[RetrievedChunk] = []
        pinned_debug: list[RetrievedSource] = []
        if use_def_resolver and register_entities:
            corpus = self._bm25.get_all_chunks(document_id)
            if corpus:
                def_matches = resolve_authoritative_definitions(
                    corpus,
                    user_query,
                    max_per_entity=1,
                    max_total=self._settings.max_pinned_definition_chunks,
                )
                pinned = pin_definition_chunks(def_matches)
                pinned_debug = [
                    _chunk_to_debug_source(c, i + 1, selected=True)
                    for i, c in enumerate(pinned)
                ]
                logger.info(
                    "Definition resolver pinned %d chunks for entities %s",
                    len(pinned),
                    register_entities,
                )

        # Vector retrieval
        query_embedding = self._embeddings.embed_query(retrieval_query)
        vector_chunks = self._vector_store.retrieve(
            document_id, query_embedding, top_k=candidate_k
        )
        for c in vector_chunks:
            c.metadata["vector_score"] = c.score
            c.metadata["retrieval_method"] = "vector"

        # BM25 retrieval
        bm25_chunks: list[RetrievedChunk] = []
        if use_hybrid:
            bm25_chunks = self._bm25.search(document_id, retrieval_query, top_k=candidate_k)

        # RRF merge
        if bm25_chunks:
            merged = _rrf_merge(vector_chunks, bm25_chunks)[: candidate_k * 2]
        else:
            merged = vector_chunks

        # Inject pinned definition chunks (dedupe, high priority)
        if pinned:
            pinned_ids = {c.chunk_id for c in pinned}
            merged = pinned + [c for c in merged if c.chunk_id not in pinned_ids]

        # Entity boost
        boosted = merged
        if use_entity_boost:
            boosted = apply_entity_boost(
                merged,
                entities,
                boost_per_hit=self._settings.entity_boost_weight,
            )

        # Definitional boost for register/flag queries
        if use_def_boost:
            boosted = apply_definitional_boost(
                boosted,
                core_query,
                boost_weight=self._settings.definitional_boost_weight,
            )

        timings.retrieval_ms = (time.perf_counter() - t0) * 1000.0

        # Cross-encoder rerank (pool includes pinned; merge guarantees they survive)
        t_rerank = time.perf_counter()
        rerank_pool = boosted
        rerank_k = min(len(rerank_pool), candidate_k + len(pinned))
        if use_rerank:
            reranked_pool = self._reranker.rerank(core_query, rerank_pool, top_k=rerank_k)
        else:
            reranked_pool = rerank_pool[:rerank_k]
        timings.rerank_ms = (time.perf_counter() - t_rerank) * 1000.0

        final_chunks = merge_pinned_with_reranked(pinned, reranked_pool, top_k=final_k)
        final_chunks = sort_definition_first(final_chunks, register_entities)

        pinned_ids = [c.chunk_id for c in pinned]
        sufficiency_raw = assess_sufficiency(
            final_chunks, user_query, pinned_chunk_ids=pinned_ids
        )
        sufficiency = EvidenceSufficiency(
            sufficient=sufficiency_raw.sufficient,
            confidence=sufficiency_raw.confidence,
            coverage_score=sufficiency_raw.coverage_score,
            coverage=EvidenceCoverage(
                definition=sufficiency_raw.coverage.definition,
                behavior=sufficiency_raw.coverage.behavior,
                exceptions=sufficiency_raw.coverage.exceptions,
                interactions=sufficiency_raw.coverage.interactions,
                query_relevance=sufficiency_raw.coverage.query_relevance,
                total_weighted=sufficiency_raw.coverage.total_weighted,
                missing_categories=sufficiency_raw.coverage.missing,
            ),
            message=sufficiency_raw.message,
            entity_mentions=sufficiency_raw.entity_mentions,
            definitional_hits=sufficiency_raw.definitional_hits,
            top_rerank_score=sufficiency_raw.top_rerank_score,
            authoritative_definitions_found=sufficiency_raw.authoritative_definitions_found,
            missing_definition_entities=sufficiency_raw.missing_definition_entities,
            pinned_chunk_ids=sufficiency_raw.pinned_chunk_ids,
        )

        # Build debug info
        debug = RetrievalDebugInfo(
            original_query=original_query,
            core_query=core_query,
            retrieval_query=retrieval_query,
            entities_detected=entity_list,
            retrieval_confidence=sufficiency.confidence,
            evidence_coverage=sufficiency.coverage.model_dump(),
            pinned_chunks=pinned_debug,
            vector_candidates=[
                _chunk_to_debug_source(c, i + 1) for i, c in enumerate(vector_chunks[:10])
            ],
            bm25_candidates=[
                _chunk_to_debug_source(c, i + 1) for i, c in enumerate(bm25_chunks[:10])
            ],
            merged_candidates=[
                _chunk_to_debug_source(c, i + 1) for i, c in enumerate(boosted[:15])
            ],
        )

        selected_ids = {c.chunk_id for c in final_chunks}
        debug.selected_chunks = [
            _chunk_to_debug_source(c, i + 1, selected=True)
            for i, c in enumerate(final_chunks)
        ]
        debug.rejected_chunks = [
            _chunk_to_debug_source(c, i + 1, selected=False)
            for i, c in enumerate(boosted)
            if c.chunk_id not in selected_ids
        ][:10]

        sources = [
            RetrievedSource(
                source_index=i,
                chunk_id=c.chunk_id,
                page_number=c.page_number,
                vector_score=float(c.metadata.get("vector_score", 0.0)),
                rerank_score=float(c.metadata.get("rerank_score", c.score)),
                bm25_score=float(c.metadata.get("bm25_score", 0.0)) or None,
                rrf_score=float(c.metadata.get("rrf_score", 0.0)) or None,
                entity_hits=int(c.metadata.get("entity_hits", 0)),
                excerpt=c.text[:280] + ("…" if len(c.text) > 280 else ""),
                selected=True,
            )
            for i, c in enumerate(final_chunks, start=1)
        ]

        context = format_context(final_chunks)
        logger.info(
            "Hybrid retrieval: pinned=%d vector=%d bm25=%d merged=%d final=%d entities=%s",
            len(pinned),
            len(vector_chunks),
            len(bm25_chunks),
            len(merged),
            len(final_chunks),
            entity_list,
        )

        return RetrievalResult(
            chunks=final_chunks,
            context=context,
            sources=sources,
            debug=debug,
            sufficiency=sufficiency,
            timings=timings,
        )
