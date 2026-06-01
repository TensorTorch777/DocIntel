"""Tests for claim refutation detection and verification abstention logic."""

import pytest

from app.services.claim_refutation import detect_claim_refutation
from app.services.evidence_sufficiency import assess_sufficiency, measure_coverage
from app.services.query_intent import QueryIntent, classify_query_intent
from app.services.vector_store import RetrievedChunk

CR3_FAULT_QUERY = "Does CR3 store the faulting address during a page fault?"
PG_VALIDATION = "CR0.PG means Page Global Enable. Is this correct?"
CR2_PDBR_QUERY = "Is CR2 the page-directory base register?"

CR2_FAULT_CHUNK = RetrievedChunk(
    chunk_id="cr2-fault",
    text=(
        "7-46 Vol. 3A INTERRUPT AND EXCEPTION HANDLING • The contents of the CR2 register. "
        "The processor loads the CR2 register with the linear address that generated the exception."
    ),
    page_number=3390,
    chunk_index=0,
    score=0.9,
    metadata={"rerank_score": 1.0},
)

CR3_PDBR_CHUNK = RetrievedChunk(
    chunk_id="cr3-pdbr",
    text="CR3 — Page-Directory-Base Register (PDBR)",
    page_number=2500,
    chunk_index=0,
    score=0.9,
    metadata={"rerank_score": 0.95},
)

CR0_PG_CHUNK = RetrievedChunk(
    chunk_id="cr0-pg",
    text="PG — Paging (bit 31 of CR0)",
    page_number=2100,
    chunk_index=0,
    score=0.9,
    metadata={"rerank_score": 1.0},
)

CR4_PGE_CHUNK = RetrievedChunk(
    chunk_id="cr4-pge",
    text="PGE — Page Global Enable (bit 7 of CR4)",
    page_number=2101,
    chunk_index=0,
    score=0.9,
    metadata={"rerank_score": 0.9},
)


class TestClaimRefutation:
    def test_cr3_fault_address_refuted_by_cr2_evidence(self):
        refutation = detect_claim_refutation([CR2_FAULT_CHUNK], CR3_FAULT_QUERY)
        assert refutation is not None
        assert refutation.queried_entity == "CR3"
        assert refutation.alternative_entity == "CR2"
        assert "linear address" in refutation.evidence_text.lower()

    def test_cr3_fault_query_not_gated_when_refutation_present(self):
        result = assess_sufficiency([CR2_FAULT_CHUNK], CR3_FAULT_QUERY)
        assert result.sufficient is True
        assert result.refutation is not None
        assert result.confidence == "high"
        assert result.message is None

    def test_cr0_pg_validation_refutation(self):
        refutation = detect_claim_refutation(
            [CR0_PG_CHUNK, CR4_PGE_CHUNK], PG_VALIDATION
        )
        assert refutation is not None
        assert refutation.queried_entity == "CR0.PG"
        assert "Paging" in refutation.evidence_text

    def test_cr2_not_page_directory_base(self):
        refutation = detect_claim_refutation([CR3_PDBR_CHUNK], CR2_PDBR_QUERY)
        assert refutation is not None
        assert refutation.queried_entity == "CR2"
        assert refutation.alternative_entity == "CR3"

    def test_verification_intent_for_does_query(self):
        intent = classify_query_intent(CR3_FAULT_QUERY)
        assert intent.intent == QueryIntent.VERIFICATION

    def test_verification_coverage_without_queried_entity_mention(self):
        coverage = measure_coverage([CR2_FAULT_CHUNK], CR3_FAULT_QUERY)
        assert coverage.exceptions >= 0.5 or coverage.behavior >= 0.25


@pytest.mark.parametrize(
    "query,chunks,expect_sufficient,expect_refutation",
    [
        (CR3_FAULT_QUERY, [CR2_FAULT_CHUNK], True, True),
        (PG_VALIDATION, [CR0_PG_CHUNK, CR4_PGE_CHUNK], True, True),
        (CR2_PDBR_QUERY, [CR3_PDBR_CHUNK], True, True),
    ],
)
def test_abstention_matrix(query, chunks, expect_sufficient, expect_refutation):
    result = assess_sufficiency(chunks, query)
    assert result.sufficient is expect_sufficient
    assert (result.refutation is not None) is expect_refutation
