"""Retrieval-Augmented Generation with hybrid retrieval, grounding, and verification."""

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from app.config import Settings
from app.models.schemas import (
    AnomalyFlag,
    AnomalyResponse,
    ChatTask,
    EvidenceSufficiency,
    SummarizeResponse,
    UnsupportedClaim,
    VerificationResult,
)
from app.services.llm import LLMService
from app.services.retrieval import RetrievalService, format_context

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = """You are a document-grounded technical assistant.

Rules:
1. Answer ONLY from retrieved context below. Never use prior knowledge.
2. If evidence is insufficient, respond exactly: "Insufficient retrieved evidence."
3. Every factual claim must be supported by retrieved evidence with inline [Source N] citations.
4. Prefer quoting exact terminology, register names, bit names, and values from sources.
5. Do not invent section names, page references, or register meanings.
6. If retrieved evidence conflicts, state the conflict and cite both sources.
7. For register/bit questions, list exact states as bullets with a citation per item.
8. Internally ensure each claim maps to: answer claim → evidence quote → source page → chunk id.
9. Do not use markdown code fences unless the user explicitly requests JSON.
10. Sources tagged AUTHORITATIVE DEFINITION or DEFINITION must be used for bit numbers and names.
11. Never infer bit positions from paging usage or procedural passages.
12. For differentiate/compare questions, cite one definition source per register/flag.

If the user requests JSON, output ONLY valid JSON with no preamble."""

CONSERVATIVE_QA_PROMPT = """You are a document-grounded technical assistant.

Rules:
1. State ONLY facts explicitly present in the retrieved sources below.
2. Do NOT infer behavior, exceptions, interactions, or semantics beyond what sources state verbatim.
3. If sources only name a register/flag without defining it, say exactly that with [Source N] citations.
4. Every sentence must have a [Source N] citation.
5. Do not use prior knowledge. Do not add #GP, paging, or exception details unless sources state them."""

REWRITE_SYSTEM_PROMPT = """Rewrite the answer using ONLY supported evidence from the retrieved sources.

Rules:
1. Remove ALL unsupported claims listed below.
2. Do not add new information.
3. Keep [Source N] citations for every remaining claim.
4. If nothing is supported, respond: "Insufficient retrieved evidence."
5. Preserve exact register and bit terminology from sources."""

VERIFY_SYSTEM_PROMPT = """Verify whether an answer is grounded in retrieved sources.

Return ONLY valid JSON:
{
  "supported": true,
  "total_claims": 0,
  "unsupported_claims": [
    {"claim": "unsupported statement", "reason": "why unsupported", "evidence": "optional"}
  ],
  "hallucination_risk": "low",
  "notes": ""
}

Rules:
- Count every distinct factual claim in the answer as total_claims
- supported=false if ANY claim lacks explicit source support
- Flag invented exception behavior (e.g. "NXE causes #GP" when sources never mention #GP)
- Flag invented semantics, paging interactions, or register definitions
- unsupported_claims may be strings OR objects with claim/reason/evidence
- hallucination_risk: low | medium | high"""

SUMMARIZE_SYSTEM_PROMPT = """You are DocIntel summarizing a technical manual.

Rules:
1. Use ONLY retrieved sources. No prior knowledge.
2. Cite [Source N] for each major claim.
3. If evidence missing, write "Insufficient retrieved evidence."
4. Do not invent specifications or register meanings."""

ANOMALY_SYSTEM_PROMPT = """Scan sources for inconsistencies. Output ONLY valid JSON:
{"flags":[{"parameter":"","description":"","severity":"low|medium|high","source_excerpt":"","source_id":"Source N"}],"summary":""}"""

_JSON_QUERY = re.compile(r"\bjson\b|structured output|schema", re.I)
_CITATION_PATTERN = re.compile(r"\[Source\s+\d+\]", re.I)


class RAGService:
    """Grounded Q&A with hybrid retrieval, verification, and optional rewrite."""

    def __init__(
        self,
        settings: Settings,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
    ) -> None:
        self._settings = settings
        self._retrieval = retrieval_service
        self._llm = llm_service

    async def stream_chat_events(
        self,
        document_id: str,
        query: str,
        task: ChatTask = ChatTask.QA,
        top_k: int | None = None,
        debug: bool = False,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """Retrieve, generate, verify, optionally rewrite; yield SSE events."""
        try:
            result = await self._retrieval.retrieve(document_id, query, top_k)
            sources = result.sources
            context = result.context
            sufficiency = result.sufficiency

            yield ("sources", {"sources": [s.model_dump() for s in sources]})
            if debug:
                yield ("debug", result.debug.to_dict())

            # Pre-generation evidence sufficiency gate
            if (
                task == ChatTask.QA
                and self._settings.enable_evidence_sufficiency_gate
                and not sufficiency.sufficient
            ):
                gated_answer = sufficiency.message or "Insufficient retrieved evidence."
                yield ("token", {"content": gated_answer})
                done_payload: dict[str, Any] = {
                    "status": "complete",
                    "document_id": document_id,
                    "task": task.value,
                    "sources": [s.model_dump() for s in sources],
                    "evidence_sufficiency": sufficiency.model_dump(),
                    "retrieval_confidence": sufficiency.confidence,
                    "gated": True,
                }
                if debug:
                    done_payload["retrieval_debug"] = result.debug.to_dict()
                yield ("done", done_payload)
                return

            system_prompt, user_prompt = self._build_prompts(task, query, context)
            temperature = self._temperature_for_query(query, task)

            answer_parts: list[str] = []
            async for token in self._llm.stream_completion(
                system_prompt, user_prompt, temperature=temperature
            ):
                answer_parts.append(token)
                yield ("token", {"content": token})

            answer = "".join(answer_parts)
            final_answer = answer
            verification = None

            if self._settings.enable_answer_verification and answer.strip():
                verification = await self._verify_answer(context, query, answer)
                if verification is not None:
                    try:
                        final_answer, verification = await self._apply_verification_actions(
                            context, query, answer, verification
                        )
                        if final_answer != answer:
                            yield ("revision", {"content": final_answer})
                    except Exception:
                        logger.warning(
                            "Answer verification actions failed; returning original answer",
                            exc_info=True,
                        )

            done_payload = {
                "status": "complete",
                "document_id": document_id,
                "task": task.value,
                "sources": [s.model_dump() for s in sources],
                "final_answer": final_answer if final_answer != answer else None,
                "evidence_sufficiency": sufficiency.model_dump(),
                "retrieval_confidence": sufficiency.confidence,
            }
            if verification:
                done_payload["verification"] = verification.model_dump()
            if debug:
                done_payload["retrieval_debug"] = result.debug.to_dict()

            yield ("done", done_payload)
        except Exception as exc:
            logger.exception("RAG stream failed")
            yield ("error", {"message": str(exc)})

    async def stream_chat(
        self,
        document_id: str,
        query: str,
        task: ChatTask = ChatTask.QA,
        top_k: int | None = None,
    ) -> AsyncIterator[str]:
        async for event, data in self.stream_chat_events(document_id, query, task, top_k):
            if event == "token":
                yield data.get("content", "")
            elif event == "revision":
                yield data.get("content", "")

    async def answer_question(
        self,
        document_id: str,
        query: str,
        top_k: int | None = None,
    ) -> str:
        result = await self._retrieval.retrieve(document_id, query, top_k)
        if (
            self._settings.enable_evidence_sufficiency_gate
            and not result.sufficiency.sufficient
        ):
            return result.sufficiency.message or "Insufficient retrieved evidence."

        _, user_prompt = self._build_prompts(ChatTask.QA, query, result.context)
        answer = await self._llm.complete(
            QA_SYSTEM_PROMPT,
            user_prompt,
            temperature=self._temperature_for_query(query, ChatTask.QA),
        )
        if self._settings.enable_answer_verification:
            try:
                v = await self._verify_answer(result.context, query, answer)
                if v is not None:
                    answer, _ = await self._apply_verification_actions(
                        result.context, query, answer, v
                    )
            except Exception:
                logger.warning(
                    "Answer verification/rewrite failed; returning original answer",
                    exc_info=True,
                )
        return answer

    async def summarize(
        self,
        document_id: str,
        focus: str | None = None,
    ) -> SummarizeResponse:
        query = focus or "executive overview key specifications architecture"
        result = await self._retrieval.retrieve(document_id, query, top_k=8)
        focus_note = f"\nFocus: {focus}" if focus else ""
        user_prompt = f"Summarize sources.{focus_note}\n\n{result.context}"
        summary = await self._llm.complete(
            SUMMARIZE_SYSTEM_PROMPT, user_prompt,
            temperature=self._settings.llm_temperature_technical,
        )
        return SummarizeResponse(
            document_id=document_id,
            summary=summary,
            sections=self._parse_summary_sections(summary),
            sources=result.sources,
        )

    async def detect_anomalies(
        self,
        document_id: str,
        parameters: list[str] | None = None,
    ) -> AnomalyResponse:
        query = " ".join(parameters) if parameters else (
            "inconsistent parameters contradictions register values tolerances"
        )
        result = await self._retrieval.retrieve(document_id, query, top_k=10)
        param_note = f"\nFocus: {', '.join(parameters)}" if parameters else ""
        user_prompt = f"Scan for anomalies.{param_note}\n\n{result.context}"
        raw = await self._llm.complete(ANOMALY_SYSTEM_PROMPT, user_prompt, temperature=0.0)
        flags, summary = self._parse_anomaly_response(raw)
        return AnomalyResponse(
            document_id=document_id,
            flags=flags,
            raw_analysis=summary,
            sources=result.sources,
        )

    async def retrieve_only(
        self,
        document_id: str,
        query: str,
        top_k: int | None = None,
    ):
        """Expose retrieval for benchmark/debug without generation."""
        return await self._retrieval.retrieve(document_id, query, top_k)

    async def verify_answer_public(
        self, context: str, query: str, answer: str
    ) -> VerificationResult | None:
        return await self._verify_answer(context, query, answer)

    @staticmethod
    def count_citations(text: str) -> int:
        return len(_CITATION_PATTERN.findall(text))

    @staticmethod
    def _build_prompts(task: ChatTask, query: str, context: str) -> tuple[str, str]:
        json_note = ""
        if _JSON_QUERY.search(query):
            json_note = "\n\nRespond with ONLY valid JSON. No markdown fences. No preamble."

        prompts = {
            ChatTask.QA: (QA_SYSTEM_PROMPT, f"Sources:\n{context}\n\nQuestion: {query}{json_note}"),
            ChatTask.SUMMARIZE: (
                SUMMARIZE_SYSTEM_PROMPT,
                f"Sources:\n{context}\n\nSummarize.{json_note}" + (f"\n\nFocus: {query}" if query else ""),
            ),
            ChatTask.ANOMALY: (
                ANOMALY_SYSTEM_PROMPT,
                f"Sources:\n{context}\n\nScan for anomalies.{json_note}" + (f"\n\nFocus: {query}" if query else ""),
            ),
        }
        return prompts.get(task, prompts[ChatTask.QA])

    def _temperature_for_query(self, query: str, task: ChatTask) -> float:
        if task == ChatTask.ANOMALY or _JSON_QUERY.search(query):
            return 0.0
        if task in (ChatTask.QA, ChatTask.SUMMARIZE):
            return self._settings.llm_temperature_technical
        return self._settings.llm_temperature

    async def _apply_verification_actions(
        self,
        context: str,
        query: str,
        answer: str,
        verification: VerificationResult,
    ) -> tuple[str, VerificationResult]:
        """Rewrite, regenerate conservatively, or pass through based on claim ratio."""
        if verification.supported or not verification.unsupported_claims:
            return answer, verification

        threshold = self._settings.unsupported_claim_threshold
        if verification.unsupported_ratio > threshold:
            regenerated = await self._regenerate_conservative(context, query)
            if regenerated.strip():
                return regenerated, VerificationResult(
                    supported=True,
                    unsupported_claims=[],
                    hallucination_risk="low",
                    notes=(
                        f"Answer regenerated conservatively "
                        f"({verification.unsupported_ratio:.0%} claims unsupported)."
                    ),
                    regenerated=True,
                    total_claims=verification.total_claims,
                    unsupported_ratio=0.0,
                )

        if self._settings.enable_answer_rewrite:
            rewritten = await self._rewrite_answer(
                context, query, answer, verification.unsupported_claims
            )
            if rewritten.strip() and rewritten.strip() != answer.strip():
                return rewritten, VerificationResult(
                    supported=True,
                    unsupported_claims=[],
                    hallucination_risk="low",
                    notes="Answer rewritten to remove unsupported claims.",
                    rewritten=True,
                    total_claims=verification.total_claims,
                    unsupported_ratio=0.0,
                )

        return answer, verification

    async def _regenerate_conservative(self, context: str, query: str) -> str:
        user_prompt = f"Sources:\n{context}\n\nQuestion: {query}"
        return await self._llm.complete(
            CONSERVATIVE_QA_PROMPT, user_prompt, temperature=0.0
        )

    async def _verify_answer(
        self, context: str, query: str, answer: str
    ) -> VerificationResult | None:
        try:
            raw = await self._llm.complete(
                VERIFY_SYSTEM_PROMPT,
                f"Question:\n{query}\n\nSources:\n{context}\n\nAnswer:\n{answer}",
                temperature=0.0,
            )
            return self._parse_verification(raw)
        except Exception:
            logger.warning("Answer verification failed; skipping rewrite", exc_info=True)
            return None

    async def _rewrite_answer(
        self,
        context: str,
        query: str,
        answer: str,
        unsupported: list[UnsupportedClaim],
    ) -> str:
        claims = "\n".join(
            f"- {c.claim}" + (f" ({c.reason})" if c.reason else "")
            for c in unsupported
        )
        user_prompt = (
            f"Question:\n{query}\n\nSources:\n{context}\n\n"
            f"Original answer:\n{answer}\n\nUnsupported claims to remove:\n{claims}"
        )
        return await self._llm.complete(REWRITE_SYSTEM_PROMPT, user_prompt, temperature=0.0)

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
            return RAGService._enrich_verification_metrics(verification)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("Verification parse failed: %s", exc)
            return None

    @staticmethod
    def _enrich_verification_metrics(
        verification: VerificationResult,
    ) -> VerificationResult:
        """Compute unsupported_ratio from total_claims and unsupported list."""
        unsupported_count = len(verification.unsupported_claims)
        total = verification.total_claims
        if total <= 0:
            total = max(unsupported_count, RAGService._estimate_claim_count(verification))
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

    @staticmethod
    def _estimate_claim_count(verification: VerificationResult) -> int:
        """Fallback when verifier omits total_claims."""
        n = len(verification.unsupported_claims)
        if verification.supported:
            return max(n, 1)
        return max(n, 1)

    @staticmethod
    def _parse_summary_sections(summary: str) -> list[str]:
        headers = re.findall(r"^#{1,3}\s+(.+)$|^\d+\.\s+(.+)$", summary, re.MULTILINE)
        return [h[0] or h[1] for h in headers if h[0] or h[1]]

    @staticmethod
    def _parse_anomaly_response(raw: str) -> tuple[list[AnomalyFlag], str | None]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        json_start = cleaned.find("{")
        if json_start > 0:
            cleaned = cleaned[json_start:]
        try:
            data = json.loads(cleaned)
            flags = [
                AnomalyFlag(
                    parameter=f.get("parameter", "unknown"),
                    description=f.get("description", ""),
                    severity=f.get("severity", "medium"),
                    source_excerpt=f.get("source_excerpt", ""),
                )
                for f in data.get("flags", [])
            ]
            return flags, data.get("summary")
        except (json.JSONDecodeError, KeyError, TypeError):
            return [], raw
