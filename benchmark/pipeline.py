"""Retrieval and RAG pipeline mode presets for baseline comparison."""

from dataclasses import dataclass
from enum import Enum


class PipelineMode(str, Enum):
    """Benchmark pipeline presets."""

    VECTOR_ONLY = "vector_only"
    VECTOR_BM25 = "vector_bm25"
    HYBRID_RERANK = "hybrid_rerank"
    FULL = "full"


@dataclass(frozen=True)
class PipelineConfig:
    """Resolved pipeline flags for a benchmark run."""

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

    @property
    def label(self) -> str:
        labels = {
            (False, False): "A · Vector only",
            (True, False): "B · Vector + BM25",
            (True, True): "C · Hybrid + rerank",
        }
        if self.evidence_gate and self.verification:
            return "D · Full pipeline"
        key = (self.hybrid, self.rerank)
        return labels.get(key, "Custom")


ALL_MODES: list[PipelineMode] = list(PipelineMode)
