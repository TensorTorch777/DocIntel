"""RAG benchmark runner for retrieval and grounding evaluation."""

import json
import logging
import re

from app.config import get_settings
from app.models.schemas import (
    BenchmarkCase,
    BenchmarkCaseResult,
    BenchmarkRequest,
    BenchmarkResponse,
)
from app.services.rag import RAGService

logger = logging.getLogger(__name__)

DEFAULT_BENCHMARK_CASES: list[BenchmarkCase] = [
    BenchmarkCase(
        query="Does CR3 store the faulting address during a page fault?",
        expected_terms=["CR2", "page-fault", "linear address"],
        forbidden_claims=["CR3 stores the faulting address"],
    ),
    BenchmarkCase(
        query="What is CR0.PG?",
        expected_terms=["CR0", "PG", "paging"],
        forbidden_claims=["Page Global"],
    ),
    BenchmarkCase(
        query="Explain canonical addressing in 64-bit mode",
        expected_terms=["canonical", "64-bit", "linear address"],
    ),
    BenchmarkCase(
        query="List steps to enter IA-32e mode",
        expected_terms=["CR4", "PAE", "EFER", "LME", "CR0", "PG"],
    ),
    BenchmarkCase(
        query="Output JSON with fields register and role for CR2 and CR3",
        expected_terms=["CR2", "CR3"],
        requires_json=True,
    ),
]


class BenchmarkService:
    """Run repeatable benchmark cases and compute aggregate scores."""

    def __init__(self, rag_service: RAGService) -> None:
        self._rag = rag_service

    async def run(self, request: BenchmarkRequest) -> BenchmarkResponse:
        cases = request.cases or DEFAULT_BENCHMARK_CASES
        results: list[BenchmarkCaseResult] = []

        for case in cases:
            result = await self._run_case(request.document_id, case)
            results.append(result)

        n = len(results) or 1
        return BenchmarkResponse(
            document_id=request.document_id,
            case_count=len(results),
            retrieval_accuracy=sum(r.retrieval_hit for r in results) / n,
            grounding_score=sum(r.grounding_supported for r in results) / n,
            format_compliance=sum(r.format_compliant for r in results) / n,
            avg_citations=sum(r.citation_count for r in results) / n,
            results=results,
        )

    async def _run_case(self, document_id: str, case: BenchmarkCase) -> BenchmarkCaseResult:
        retrieval = await self._rag.retrieve_only(document_id, case.query)
        combined_text = " ".join(c.text for c in retrieval.chunks).upper()

        matched = [t for t in case.expected_terms if t.upper() in combined_text]
        retrieval_hit = len(matched) >= max(1, len(case.expected_terms) // 2)

        answer = await self._rag.answer_question(document_id, case.query)
        verification = None
        if get_settings().enable_answer_verification:
            verification = await self._rag.verify_answer_public(
                retrieval.context, case.query, answer
            )

        grounding_supported = verification.supported if verification else True
        format_compliant = True
        if case.requires_json:
            try:
                cleaned = answer.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
                    cleaned = re.sub(r"\n?```$", "", cleaned)
                json.loads(cleaned[cleaned.find("{") :])
            except (json.JSONDecodeError, ValueError):
                format_compliant = False

        for forbidden in case.forbidden_claims:
            if forbidden.lower() in answer.lower():
                grounding_supported = False

        return BenchmarkCaseResult(
            query=case.query,
            retrieval_hit=retrieval_hit,
            matched_terms=matched,
            grounding_supported=grounding_supported,
            hallucination_risk=verification.hallucination_risk if verification else "unknown",
            format_compliant=format_compliant,
            citation_count=self._rag.count_citations(answer),
            answer_preview=answer[:400],
            retrieval_query=retrieval.debug.retrieval_query,
        )
