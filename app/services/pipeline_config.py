"""Retrieval pipeline mode presets for optional runtime overrides."""

from dataclasses import dataclass
from enum import Enum


class PipelineMode(str, Enum):
    """Pipeline presets from minimal retrieval to full RAG."""

    VECTOR_ONLY = "vector_only"
    VECTOR_BM25 = "vector_bm25"
    HYBRID_RERANK = "hybrid_rerank"
    FULL = "full"


@dataclass(frozen=True)
class PipelineConfig:
    """Resolved pipeline flags for a retrieval run."""

    hybrid: bool
    rerank: bool
    definition_resolver: bool
    entity_boost: bool
    definitional_boost: bool
    evidence_gate: bool
    verification: bool
    rewrite: bool

    @classmethod
    def from_mode(cls, mode: PipelineMode) -> "PipelineConfig":
        presets: dict[PipelineMode, PipelineConfig] = {
            PipelineMode.VECTOR_ONLY: cls(
                hybrid=False,
                rerank=False,
                definition_resolver=False,
                entity_boost=False,
                definitional_boost=False,
                evidence_gate=False,
                verification=False,
                rewrite=False,
            ),
            PipelineMode.VECTOR_BM25: cls(
                hybrid=True,
                rerank=False,
                definition_resolver=False,
                entity_boost=False,
                definitional_boost=False,
                evidence_gate=False,
                verification=False,
                rewrite=False,
            ),
            PipelineMode.HYBRID_RERANK: cls(
                hybrid=True,
                rerank=True,
                definition_resolver=True,
                entity_boost=True,
                definitional_boost=True,
                evidence_gate=False,
                verification=False,
                rewrite=False,
            ),
            PipelineMode.FULL: cls(
                hybrid=True,
                rerank=True,
                definition_resolver=True,
                entity_boost=True,
                definitional_boost=True,
                evidence_gate=True,
                verification=True,
                rewrite=True,
            ),
        }
        return presets[mode]
