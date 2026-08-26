"""Retrieval-Augmented Generation with hybrid retrieval, grounding, and verification."""

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from app.config import Settings
from app.services.pipeline_config import PipelineConfig
from app.models.schemas import (
    AnomalyFlag,
    AnomalyResponse,
    ChatTask,
    EvidenceSufficiency,
    RetrievedSource,
    SummarizeResponse,
    UnsupportedClaim,
    VerificationResult,
)
from app.services.answer_verification import AnswerVerificationService
from app.services.claim_refutation import ClaimRefutation, detect_claim_refutation
from app.services.moe import route_experts
from app.services.llm import LLMService
from app.services.pipeline_events import StageStatus, pipeline_event
from app.services.procedural_reasoning import (
    PROCEDURAL_SYSTEM_PROMPT,
    build_procedural_user_prompt,
    generate_procedural_answer_from_evidence,
)
from app.services.query_intent import (
    AnswerTemplate,
    QueryIntent,
    classify_query_intent,
)
from app.services.retrieval import RetrievalResult, RetrievalService, format_context

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

VERIFICATION_QA_PROMPT = """You are a document-grounded technical assistant validating user claims.

Rules:
1. Answer ONLY from retrieved context. Never use prior knowledge.
2. If the user's stated meaning conflicts with sources, answer NO and give the correct meaning with [Source N] citations.
3. If the user asks whether register X has role Y but sources assign Y to register Z, answer NO and name Z with citations.
4. If the user's claim matches sources, answer YES with supporting citations.
5. Be concise: state Yes/No first, then one short correction or confirmation paragraph.
6. For register flags: cite the authoritative definition passage (bit name and meaning).
7. Do not produce step-by-step procedures unless the user explicitly asked for steps.
8. Do not abstain when sources explicitly identify a different register for the same role."""

COMPARISON_QA_PROMPT = """You are a document-grounded technical assistant comparing registers, flags, or concepts.

Rules:
1. Answer ONLY from retrieved context with [Source N] citations per register/concept.
2. Structure: one bullet per entity with its definition/behavior from sources.
3. Explicitly state differences only when supported by sources.
4. If evidence is insufficient for any entity, say so for that entity only."""

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

# Legacy alias kept for imports; verification prompts live in answer_verification.py

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
        self._verifier = AnswerVerificationService(settings, llm_service)

    async def stream_chat_events(
        self,
        document_id: str,
        query: str,
        task: ChatTask = ChatTask.QA,
        top_k: int | None = None,
        debug: bool = False,
        attachment_context: str | None = None,
        attachment_modality: str | None = None,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """Retrieve, generate, verify, optionally rewrite; yield SSE events."""
        import asyncio

        pipeline_snapshot: list[dict[str, Any]] = []

        def _track(event: dict[str, Any]) -> None:
            stage = event.get("stage")
            for i, existing in enumerate(pipeline_snapshot):
                if existing.get("stage") == stage:
                    pipeline_snapshot[i] = event
                    return
            pipeline_snapshot.append(event)

        try:
            yield (
                "pipeline",
                pipeline_event("understanding_query", StageStatus.RUNNING),
            )
            await asyncio.sleep(0)
            intent_result = classify_query_intent(query or " ")
            media_kind = (attachment_modality or "").strip().lower() or None
            if not media_kind:
                try:
                    info = self._retrieval._vector_store.get_document_info(document_id)
                    media_kind = str((info or {}).get("modality") or "pdf")
                except Exception:
                    media_kind = "pdf"
            if not (query or "").strip() and attachment_context:
                query = (
                    f"Interpret the attached {media_kind} using the indexed document."
                )
            understanding = pipeline_event(
                "understanding_query",
                StageStatus.COMPLETED,
                detail={
                    "intent": intent_result.intent.value,
                    "pipeline": intent_result.pipeline.value,
                    "media_kind": media_kind,
                },
            )
            _track(understanding)
            yield ("pipeline", understanding)

            moe = route_experts(
                query,
                media_kind=media_kind or "pdf",
                has_attachment=bool(attachment_context),
                intent=intent_result.intent,
                top_k=self._settings.moe_top_k,
            )
            if self._settings.enable_moe_routing:
                moe_event = pipeline_event(
                    "moe_routing",
                    StageStatus.COMPLETED,
                    detail=moe.to_dict(),
                )
            else:
                moe_event = pipeline_event(
                    "moe_routing",
                    StageStatus.SKIPPED,
                    detail={"reason": "disabled"},
                )
            _track(moe_event)
            yield ("pipeline", moe_event)

            retrieval_query = query
            if attachment_context:
                retrieval_query = (
                    f"{query}\n\n[Attached {media_kind} evidence]\n{attachment_context}"
                )

            result = None
            async for kind, payload in self._retrieval.stream_retrieve(
                document_id, retrieval_query, top_k
            ):
                if kind == "pipeline":
                    _track(payload)
                    yield ("pipeline", payload)
                elif kind == "result":
                    result = payload

            if result is None:
                raise RuntimeError("Retrieval produced no result")

            sources = result.sources
            context = result.context
            if attachment_context:
                context = (
                    f"[ATTACHED {(media_kind or 'media').upper()} EVIDENCE]\n"
                    f"{attachment_context}\n\n{context}"
                )
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
                gate_gen = pipeline_event(
                    "answer_generation",
                    StageStatus.SKIPPED,
                    detail={"reason": "evidence gate"},
                )
                yield ("pipeline", gate_gen)
                _track(gate_gen)
                gate_verify = pipeline_event(
                    "verification",
                    StageStatus.SKIPPED,
                    detail={"reason": "evidence gate"},
                )
                yield ("pipeline", gate_verify)
                _track(gate_verify)
                yield ("token", {"content": gated_answer})
                done_payload: dict[str, Any] = {
                    "status": "complete",
                    "document_id": document_id,
                    "task": task.value,
                    "sources": [s.model_dump() for s in sources],
                    "evidence_sufficiency": sufficiency.model_dump(),
                    "retrieval_confidence": sufficiency.confidence,
                    "gated": True,
                    "pipeline": pipeline_snapshot,
                    "moe": moe.to_dict() if self._settings.enable_moe_routing else None,
                }
                if debug:
                    done_payload["retrieval_debug"] = result.debug.to_dict()
                yield ("done", done_payload)
                return

            system_prompt, user_prompt = self._build_prompts(task, query, context)
            temperature = self._temperature_for_query(query, task)

            answer_parts: list[str] = []
            refutation = detect_claim_refutation(result.chunks, query)
            use_procedural = (
                task == ChatTask.QA
                and self._settings.enable_procedural_reasoning
                and intent_result.intent == QueryIntent.PROCEDURAL
            )

            yield ("pipeline", pipeline_event("answer_generation", StageStatus.RUNNING))
            await asyncio.sleep(0)

            if refutation and task == ChatTask.QA:
                answer = self._format_refutation_answer(refutation, sources)
                yield ("token", {"content": answer})
            elif use_procedural:
                answer = await self._generate_procedural_answer(query, result)
                yield ("token", {"content": answer})
            else:
                async for token in self._llm.stream_completion(
                    system_prompt, user_prompt, temperature=temperature
                ):
                    answer_parts.append(token)
                    yield ("token", {"content": token})
                answer = "".join(answer_parts)

            gen_detail: dict[str, Any] = {"mode": intent_result.pipeline.value}
            if refutation:
                gen_detail["refutation"] = True
            gen_done = pipeline_event(
                "answer_generation",
                StageStatus.COMPLETED,
                detail=gen_detail,
            )
            _track(gen_done)
            yield ("pipeline", gen_done)

            final_answer = answer
            verification = None

            yield ("pipeline", pipeline_event("verification", StageStatus.RUNNING))
            await asyncio.sleep(0)

            verify_detail: dict[str, Any] = {"executed": False, "skipped": True}
            if self._settings.enable_answer_verification and answer.strip():
                do_verify, skip_reason = self._verifier.should_verify(
                    query, answer, result.chunks, gated=False,
                    procedural=intent_result.intent == QueryIntent.PROCEDURAL,
                )
                verify_detail = {
                    "executed": do_verify,
                    "skipped": not do_verify,
                    "skip_reason": skip_reason if not do_verify else None,
                }
                if do_verify:
                    verification = await self._verifier.verify(
                        context, query, answer, chunks=result.chunks,
                        lightweight=self._verifier.assess_risk(query, answer, result.chunks) == "medium",
                    )
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

            if verification:
                verify_detail["supported"] = verification.supported
                verify_detail["risk"] = verification.hallucination_risk

            verify_done = pipeline_event(
                "verification",
                StageStatus.COMPLETED if verify_detail.get("executed") else StageStatus.SKIPPED,
                detail=verify_detail,
            )
            _track(verify_done)
            yield ("pipeline", verify_done)

            done_payload = {
                "status": "complete",
                "document_id": document_id,
                "task": task.value,
                "sources": [s.model_dump() for s in sources],
                "final_answer": final_answer if final_answer != answer else None,
                "evidence_sufficiency": sufficiency.model_dump(),
                "retrieval_confidence": sufficiency.confidence,
                "pipeline": pipeline_snapshot,
                "moe": moe.to_dict() if self._settings.enable_moe_routing else None,
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

        intent_result = classify_query_intent(query)
        refutation = detect_claim_refutation(result.chunks, query)
        if refutation:
            return self._format_refutation_answer(refutation, result.sources)
        if self._settings.enable_procedural_reasoning and intent_result.intent == QueryIntent.PROCEDURAL:
            answer = await self._generate_procedural_answer(query, result)
        else:
            system_prompt, user_prompt = self._prompts_for_intent(intent_result, query, result.context)
            answer = await self._llm.complete(
                system_prompt,
                user_prompt,
                temperature=self._temperature_for_query(query, ChatTask.QA),
            )
        if self._settings.enable_answer_verification:
            try:
                do_verify, _ = self._verifier.should_verify(
                    query, answer, result.chunks, gated=False,
                    procedural=intent_result.intent == QueryIntent.PROCEDURAL,
                )
                if do_verify:
                    v = await self._verifier.verify(
                        result.context, query, answer, chunks=result.chunks,
                        lightweight=self._verifier.assess_risk(query, answer, result.chunks) == "medium",
                    )
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
        pipeline: PipelineConfig | None = None,
    ):
        """Expose retrieval for debug without generation."""
        return await self._retrieval.retrieve(
            document_id, query, top_k, pipeline=pipeline
        )

    async def verify_answer_public(
        self, context: str, query: str, answer: str
    ) -> VerificationResult | None:
        return await self._verifier.verify(context, query, answer)

    async def _verify_answer(
        self, context: str, query: str, answer: str
    ) -> VerificationResult | None:
        """Backward-compatible wrapper."""
        return await self._verifier.verify(context, query, answer)

    @staticmethod
    def count_citations(text: str) -> int:
        return len(_CITATION_PATTERN.findall(text))

    async def _generate_procedural_answer(self, query: str, result: RetrievalResult) -> str:
        """Procedural path: extract, query-filter, order steps, format with citations."""
        direct, ordered = generate_procedural_answer_from_evidence(
            result.chunks,
            query,
            max_steps=self._settings.procedural_max_steps,
            relevance_threshold=self._settings.procedural_relevance_threshold,
        )
        if direct:
            return direct

        user_prompt = build_procedural_user_prompt(query, result.context, ordered)
        return await self._llm.complete(
            PROCEDURAL_SYSTEM_PROMPT,
            user_prompt,
            temperature=0.0,
        )

    @staticmethod
    def _format_refutation_answer(
        refutation: ClaimRefutation,
        sources: list[RetrievedSource],
    ) -> str:
        source_index = refutation.source_index
        for source in sources:
            if source.chunk_id == refutation.chunk.chunk_id:
                source_index = source.source_index
                break
        page = refutation.chunk.page_number
        return (
            f"NO. {refutation.evidence_text.strip()} "
            f"[Source {source_index}, p. {page}]"
        )

    @staticmethod
    def _prompts_for_intent(
        intent_result,
        query: str,
        context: str,
    ) -> tuple[str, str]:
        """Select system prompt by classified intent."""
        template = intent_result.answer_template
        if template == AnswerTemplate.VERIFICATION:
            system = VERIFICATION_QA_PROMPT
        elif template == AnswerTemplate.COMPARISON:
            system = COMPARISON_QA_PROMPT
        else:
            system = QA_SYSTEM_PROMPT
        user = f"Sources:\n{context}\n\nQuestion: {query}"
        return system, user

    @staticmethod
    def _build_prompts(task: ChatTask, query: str, context: str) -> tuple[str, str]:
        json_note = ""
        if _JSON_QUERY.search(query):
            json_note = "\n\nRespond with ONLY valid JSON. No markdown fences. No preamble."

        if task == ChatTask.QA:
            intent_result = classify_query_intent(query)
            system, user = RAGService._prompts_for_intent(intent_result, query, context)
            return system, user + json_note

        prompts = {
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
