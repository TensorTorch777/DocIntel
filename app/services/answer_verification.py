"""Selective answer verification with caching and lightweight claim extraction."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import OrderedDict

from app.config import Settings
from app.models.schemas import UnsupportedClaim, VerificationResult
from app.services.citation_support import (
    citation_coverage_per_sentence,
    extract_cited_source_indices,
    extract_factual_sentences,
)
from app.services.llm import LLMService
from app.services.register_definition_resolver import (
    authoritative_coverage,
    extract_register_entities,
    is_authoritative_definition,
    requires_exact_definition,
)
from app.services.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)

VERIFY_SYSTEM_PROMPT = """Verify whether an answer is grounded in retrieved sources.

Return ONLY valid JSON:
{
  "supported": true,
  "total_claims": 0,
  "unsupported_claims": [],
  "hallucination_risk": "low",
  "notes": ""
}

Rules:
- Count every distinct factual claim as total_claims
- supported=false if ANY claim lacks explicit source support
- unsupported_claims: list of {"claim": "...", "reason": "..."} objects
- hallucination_risk: low | medium | high"""

LIGHTWEIGHT_VERIFY_PROMPT = """Verify ONLY the listed claims against sources.

Return ONLY valid JSON:
{"supported": true, "total_claims": N, "unsupported_claims": [], "hallucination_risk": "low", "notes": ""}"""


class AnswerVerificationService:
    """Conditional LLM verification with result caching."""

    def __init__(self, settings: Settings, llm: LLMService) -> None:
        self._settings = settings
        self._llm = llm
        self._cache: OrderedDict[str, VerificationResult] = OrderedDict()
        self._cache_max = settings.verification_cache_size

    def should_verify(
        self,
        query: str,
        answer: str,
        chunks: list[RetrievedChunk],
        *,
        gated: bool = False,
        procedural: bool = False,
    ) -> tuple[bool, str]:
        """Return (run_verification, skip_reason)."""
        if not self._settings.enable_answer_verification:
            return False, "disabled"
        if gated or not answer.strip():
            return False, "gated_or_empty"
        if re.search(
            r"insufficient retrieved evidence|cannot answer from (the )?provided",
            answer,
            re.I,
        ):
            return False, "abstention"

        if procedural and citation_coverage_per_sentence(answer) >= 1.0:
            return False, "procedural_fully_cited"

        if self._settings.skip_verification_authoritative_definitions and self._is_authoritative_definition_answer(
            query, answer, chunks
        ):
            return False, "authoritative_definition"

        risk = self.assess_risk(query, answer, chunks)
        if risk == "low":
            return False, "low_risk"
        return True, f"risk_{risk}"

    def assess_risk(
        self,
        query: str,
        answer: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        """Classify verification priority: low, medium, or high."""
        claims = extract_factual_sentences(answer)
        if not claims:
            return "low"

        coverage = citation_coverage_per_sentence(answer)
        if coverage < 0.5:
            return "high"
        if coverage < 1.0:
            return "medium"

        indices = extract_cited_source_indices(answer)
        if indices and max(indices, default=0) > len(chunks):
            return "high"

        if requires_exact_definition(query):
            all_covered, _ = authoritative_coverage(chunks, query)
            if not all_covered:
                return "high"

        if len(claims) >= 6:
            return "medium"
        return "low"

    def _is_authoritative_definition_answer(
        self,
        query: str,
        answer: str,
        chunks: list[RetrievedChunk],
    ) -> bool:
        if not requires_exact_definition(query):
            return False
        entities = extract_register_entities(query)
        if not entities:
            return False
        all_covered, missing = authoritative_coverage(chunks, query)
        if not all_covered:
            return False
        if citation_coverage_per_sentence(answer) < 1.0:
            return False
        # Answer should echo authoritative terminology from pinned/selected chunks
        for entity in entities:
            if entity in missing:
                return False
            if entity.upper() not in answer.upper() and entity.split(".")[-1] not in answer.upper():
                return False
        for chunk in chunks:
            if any(is_authoritative_definition(chunk.text, e) for e in entities):
                bit_match = re.search(r"\bbit\s+\d+\b", chunk.text, re.I)
                if bit_match and bit_match.group(0).lower() not in answer.lower():
                    return False
        return True

    async def verify(
        self,
        context: str,
        query: str,
        answer: str,
        *,
        chunks: list[RetrievedChunk] | None = None,
        lightweight: bool = False,
    ) -> VerificationResult | None:
        key = self._cache_key(context, query, answer)
        if key in self._cache:
            return self._cache[key]

        claims = extract_factual_sentences(answer)
        try:
            if lightweight and claims and len(claims) <= 8:
                claims_block = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
                raw = await self._llm.complete(
                    LIGHTWEIGHT_VERIFY_PROMPT,
                    f"Question:\n{query}\n\nSources:\n{context}\n\nClaims:\n{claims_block}",
                    temperature=0.0,
                )
            else:
                raw = await self._llm.complete(
                    VERIFY_SYSTEM_PROMPT,
                    f"Question:\n{query}\n\nSources:\n{context}\n\nAnswer:\n{answer}",
                    temperature=0.0,
                )
            result = self._parse_verification(raw)
            if result is not None:
                self._store_cache(key, result)
            return result
        except Exception:
            logger.warning("Answer verification failed", exc_info=True)
            return None

    def _cache_key(self, context: str, query: str, answer: str) -> str:
        payload = f"{query}\0{answer}\0{context[:800]}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def _store_cache(self, key: str, result: VerificationResult) -> None:
        self._cache[key] = result
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_max:
            self._cache.popitem(last=False)

    @staticmethod
    def _parse_verification(raw: str) -> VerificationResult | None:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        json_start = cleaned.find("{")
        if json_start > 0:
            cleaned = cleaned[json_start:]
        try:
            data = json.loads(cleaned)
            verification = VerificationResult.model_validate(data)
            return AnswerVerificationService._enrich_metrics(verification)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("Verification parse failed: %s", exc)
            return None

    @staticmethod
    def _enrich_metrics(verification: VerificationResult) -> VerificationResult:
        unsupported_count = len(verification.unsupported_claims)
        total = verification.total_claims
        if total <= 0:
            total = max(unsupported_count, 1)
        ratio = unsupported_count / total if total > 0 else 0.0

        supported = verification.supported
        risk = verification.hallucination_risk
        if ratio > 0.3:
            supported = False
            risk = "high"
        elif ratio > 0:
            supported = False
            if risk == "low":
                risk = "medium"

        return verification.model_copy(
            update={
                "total_claims": total,
                "unsupported_ratio": ratio,
                "supported": supported,
                "hallucination_risk": risk,
            }
        )
