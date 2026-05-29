"""API request and response models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ChatTask(str, Enum):
    """Supported generative RAG task types."""

    QA = "qa"
    SUMMARIZE = "summarize"
    ANOMALY = "anomaly"


class UploadResponse(BaseModel):
    """Response after successful PDF upload and indexing."""

    document_id: str = Field(..., description="Unique identifier for the indexed document")
    filename: str
    page_count: int
    chunk_count: int
    message: str = "Document indexed successfully"


class DocumentInfo(BaseModel):
    """Metadata for an indexed document."""

    document_id: str
    filename: str
    page_count: int
    chunk_count: int


class ChatRequest(BaseModel):
    """Request body for the streaming chat endpoint."""

    document_id: str = Field(..., description="ID of the indexed document to query")
    query: str = Field(..., min_length=1, description="User query or instruction")
    task: ChatTask = Field(default=ChatTask.QA, description="RAG task to perform")
    top_k: int | None = Field(
        default=None, ge=1, le=20, description="Final chunks after reranking"
    )
    debug: bool = Field(default=False, description="Include retrieval debug metadata")


class RetrievedSource(BaseModel):
    """A retrieved chunk exposed for grounding transparency."""

    source_index: int
    chunk_id: str
    page_number: int | None
    vector_score: float = 0.0
    rerank_score: float = 0.0
    bm25_score: float | None = None
    rrf_score: float | None = None
    entity_hits: int = 0
    excerpt: str
    selected: bool = True


class UnsupportedClaim(BaseModel):
    """A single unsupported factual claim flagged by the verifier."""

    claim: str
    reason: str | None = None
    evidence: str | None = None


class VerificationResult(BaseModel):
    """Answer verification against retrieved sources."""

    supported: bool
    unsupported_claims: list[UnsupportedClaim] = Field(default_factory=list)
    hallucination_risk: str = "low"
    notes: str = ""
    rewritten: bool = False
    regenerated: bool = False
    total_claims: int = 0
    unsupported_ratio: float = 0.0

    @field_validator("unsupported_claims", mode="before")
    @classmethod
    def coerce_unsupported_claims(cls, value: object) -> list[object]:
        """Accept legacy list[str] or structured dict claims from the verifier."""
        if not value:
            return []
        if not isinstance(value, list):
            return []
        coerced: list[object] = []
        for item in value:
            if isinstance(item, str):
                coerced.append({"claim": item})
            elif isinstance(item, dict):
                claim_text = item.get("claim") or item.get("text") or item.get("description")
                if claim_text:
                    coerced.append(
                        {
                            "claim": str(claim_text),
                            "reason": item.get("reason"),
                            "evidence": item.get("evidence"),
                        }
                    )
        return coerced

    def claim_texts(self) -> list[str]:
        """Plain-text claims for rewrite prompts and UI fallbacks."""
        return [c.claim for c in self.unsupported_claims if c.claim.strip()]


class EvidenceCoverage(BaseModel):
    """Per-category evidence coverage from retrieval."""

    definition: bool = False
    behavior: bool = False
    exceptions: bool = False
    interactions: bool = False
    missing_categories: list[str] = Field(default_factory=list)


class EvidenceSufficiency(BaseModel):
    """Pre-generation evidence gate result."""

    sufficient: bool
    confidence: str = "medium"  # high | medium | low
    coverage: EvidenceCoverage = Field(default_factory=EvidenceCoverage)
    message: str | None = None
    entity_mentions: int = 0
    definitional_hits: int = 0
    top_rerank_score: float = 0.0
    authoritative_definitions_found: bool = False
    missing_definition_entities: list[str] = Field(default_factory=list)
    pinned_chunk_ids: list[str] = Field(default_factory=list)


class SummarizeRequest(BaseModel):
    """Request for non-streaming summarization."""

    document_id: str
    focus: str | None = Field(
        default=None,
        description="Optional focus area (e.g. 'safety systems', 'structural loads')",
    )


class SummarizeResponse(BaseModel):
    """Structured summary response."""

    document_id: str
    summary: str
    sections: list[str] = Field(default_factory=list)
    sources: list[RetrievedSource] = Field(default_factory=list)


class AnomalyRequest(BaseModel):
    """Request for anomaly detection scan."""

    document_id: str
    parameters: list[str] | None = Field(
        default=None,
        description="Optional list of engineering parameters to inspect",
    )


class AnomalyFlag(BaseModel):
    """A single flagged inconsistency or out-of-bounds metric."""

    parameter: str
    description: str
    severity: str = Field(description="low | medium | high")
    source_excerpt: str


class AnomalyResponse(BaseModel):
    """Anomaly scan results."""

    document_id: str
    flags: list[AnomalyFlag]
    raw_analysis: str | None = None
    sources: list[RetrievedSource] = Field(default_factory=list)


class SSEEvent(BaseModel):
    """Server-Sent Event payload."""

    event: str = "message"
    data: dict[str, Any]


class BenchmarkCase(BaseModel):
    """Single benchmark test case."""

    query: str
    expected_terms: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    requires_json: bool = False


class BenchmarkRequest(BaseModel):
    """Run benchmark suite against a document."""

    document_id: str
    cases: list[BenchmarkCase] | None = None


class BenchmarkCaseResult(BaseModel):
    """Results for one benchmark case."""

    query: str
    retrieval_hit: bool
    matched_terms: list[str] = Field(default_factory=list)
    grounding_supported: bool
    hallucination_risk: str
    format_compliant: bool
    citation_count: int
    answer_preview: str
    retrieval_query: str = ""


class BenchmarkResponse(BaseModel):
    """Aggregate benchmark results."""

    document_id: str
    case_count: int
    retrieval_accuracy: float
    grounding_score: float
    format_compliance: float
    avg_citations: float
    results: list[BenchmarkCaseResult]
