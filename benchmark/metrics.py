"""Benchmark metric computations from actual run outputs."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from app.services.citation_support import (
    citation_accuracy_score,
    citation_coverage_per_sentence,
)
from app.services.register_definition_resolver import (
    extract_register_entities,
    is_authoritative_definition,
)

_ABSTAIN_RE = re.compile(
    r"insufficient retrieved evidence|cannot answer from (the )?provided|not enough evidence|"
    r"do not cover the topic|cannot answer without inference|exact register definition",
    re.I,
)
_CITATION_RE = re.compile(r"\[Source\s+\d+\]", re.I)


@dataclass
class LatencyMetrics:
    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0
    generation_ms: float = 0.0
    verification_ms: float = 0.0
    total_ms: float = 0.0


@dataclass
class CaseMetrics:
    retrieval_recall_at_k: float = 0.0
    mrr: float = 0.0
    ndcg_at_k: float = 0.0
    definition_accuracy: float | None = None
    hallucination: bool = False
    unsupported_claim_ratio: float = 0.0
    abstained: bool = False
    abstention_correct: bool | None = None
    stepwise_accuracy: float | None = None
    ordered_step_accuracy: float | None = None
    missing_step_rate: float | None = None
    extra_step_rate: float | None = None
    step_precision: float | None = None
    step_recall: float | None = None
    citation_accuracy: float = 0.0
    citation_coverage_per_sentence: float = 0.0
    definition_retrieved: bool | None = None
    definition_selected: bool | None = None
    definition_used: bool | None = None
    definition_correct: bool | None = None
    must_contain_score: float = 0.0
    must_not_violations: int = 0
    expected_chunks_hit: int = 0
    expected_chunks_total: int = 0
    latency: LatencyMetrics = field(default_factory=LatencyMetrics)


def is_abstention(answer: str, *, gated: bool = False) -> bool:
    if gated:
        return True
    text = (answer or "").strip()
    if not text:
        return True
    return bool(_ABSTAIN_RE.search(text))


def chunk_matches_pattern(chunk_text: str, pattern: str) -> bool:
    return pattern.lower() in chunk_text.lower()


def relevant_ranks(
    retrieved_texts: list[str],
    expected_chunks: list[str],
) -> list[int]:
    """1-based ranks of first hit for each expected chunk pattern."""
    ranks: list[int] = []
    for pattern in expected_chunks:
        for i, text in enumerate(retrieved_texts, start=1):
            if chunk_matches_pattern(text, pattern):
                ranks.append(i)
                break
    return ranks


def retrieval_recall_at_k(
    retrieved_texts: list[str],
    expected_chunks: list[str],
    k: int,
) -> float:
    if not expected_chunks:
        return 1.0
    top = retrieved_texts[:k]
    hits = sum(
        1 for pattern in expected_chunks if any(chunk_matches_pattern(t, pattern) for t in top)
    )
    return hits / len(expected_chunks)


def mrr(retrieved_texts: list[str], expected_chunks: list[str]) -> float:
    if not expected_chunks:
        return 1.0
    ranks = relevant_ranks(retrieved_texts, expected_chunks)
    if not ranks:
        return 0.0
    return sum(1.0 / r for r in ranks) / len(expected_chunks)


def ndcg_at_k(
    retrieved_texts: list[str],
    expected_chunks: list[str],
    k: int,
) -> float:
    """
    NDCG@k with binary relevance per expected pattern (each counted once).

    Each expected chunk pattern contributes gain at its first matching rank.
    Result is clamped to [0.0, 1.0].
    """
    if not expected_chunks:
        return 1.0

    top = retrieved_texts[:k]
    gains: list[float] = []
    for pattern in expected_chunks:
        for rank, text in enumerate(top, start=1):
            if chunk_matches_pattern(text, pattern):
                gains.append(1.0 / math.log2(rank + 1))
                break

    ideal_n = min(len(expected_chunks), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_n + 1))
    if idcg <= 0:
        return 0.0
    return min(1.0, sum(gains) / idcg)


def must_contain_score(answer: str, must_contain: list[str]) -> float:
    if not must_contain:
        return 1.0
    answer_l = answer.lower()
    hits = sum(1 for term in must_contain if term.lower() in answer_l)
    return hits / len(must_contain)


def must_not_violations(answer: str, must_not_contain: list[str]) -> int:
    answer_l = answer.lower()
    return sum(1 for term in must_not_contain if term.lower() in answer_l)


def stepwise_accuracy(answer: str, expected_steps: list[str]) -> float:
    if not expected_steps:
        return 1.0
    answer_l = answer.lower()
    pos = 0
    matched = 0
    for step in expected_steps:
        idx = answer_l.find(step.lower(), pos)
        if idx >= 0:
            matched += 1
            pos = idx + len(step)
    return matched / len(expected_steps)


def ordered_step_accuracy(answer: str, expected_steps: list[str]) -> float:
    """Ordered step match requiring Step N: structure when present."""
    if not expected_steps:
        return 1.0
    base = stepwise_accuracy(answer, expected_steps)
    has_step_format = bool(re.search(r"Step\s+\d+\s*:", answer, re.I))
    if has_step_format:
        return base
    return base * 0.85


def missing_step_rate(answer: str, expected_steps: list[str]) -> float:
    if not expected_steps:
        return 0.0
    answer_l = answer.lower()
    missing = sum(1 for step in expected_steps if step.lower() not in answer_l)
    return missing / len(expected_steps)


def extra_step_rate(answer: str, expected_steps: list[str]) -> float:
    if not expected_steps:
        return 0.0
    step_lines = re.findall(r"Step\s+\d+\s*:", answer, re.I)
    if not step_lines:
        bullet_lines = len(re.findall(r"^\s*\d+[\.)]\s+", answer, re.MULTILINE))
        extra = max(0, bullet_lines - len(expected_steps))
    else:
        extra = max(0, len(step_lines) - len(expected_steps))
    return min(1.0, extra / len(expected_steps))


_STEP_LINE = re.compile(
    r"Step\s+\d+\s*:\s*(.+?)(?:\s*\[Source\s+\d+\]|\s*$)",
    re.I | re.MULTILINE,
)


def extract_procedural_answer_steps(answer: str) -> list[str]:
    """Parse Step N: lines from a procedural answer."""
    lines = [m.group(1).strip() for m in _STEP_LINE.finditer(answer)]
    if lines:
        return lines
    for part in re.split(r"Step\s+\d+\s*:", answer, flags=re.I)[1:]:
        text = re.split(r"\[Source\s+\d+\]", part, maxsplit=1, flags=re.I)[0].strip()
        if text:
            lines.append(text)
    return lines


def _step_covers_expected(answer_step: str, expected: str) -> bool:
    a = answer_step.lower()
    e = expected.lower().strip()
    if not e:
        return False
    if e in a:
        return True
    e_tokens = set(re.findall(r"[a-z0-9]{3,}", e))
    a_tokens = set(re.findall(r"[a-z0-9]{3,}", a))
    if e_tokens and len(e_tokens & a_tokens) / len(e_tokens) >= 0.5:
        return True
    return False


def step_recall(answer: str, expected_steps: list[str]) -> float:
    if not expected_steps:
        return 1.0
    ans_steps = extract_procedural_answer_steps(answer)
    hits = sum(
        1 for e in expected_steps if any(_step_covers_expected(a, e) for a in ans_steps)
    )
    return hits / len(expected_steps)


def step_precision(answer: str, expected_steps: list[str]) -> float:
    if not expected_steps:
        return 1.0
    ans_steps = extract_procedural_answer_steps(answer)
    if not ans_steps:
        return 0.0
    hits = sum(
        1 for a in ans_steps if any(_step_covers_expected(a, e) for e in expected_steps)
    )
    return hits / len(ans_steps)


def citation_accuracy(
    answer: str,
    *,
    should_abstain: bool,
    has_sources: bool,
    num_sources: int = 0,
    retrieved_texts: list[str] | None = None,
) -> float:
    return citation_accuracy_score(
        answer,
        should_abstain=should_abstain,
        has_sources=has_sources,
        num_sources=num_sources,
        retrieved_texts=retrieved_texts,
    )


def compute_definition_funnel(
    *,
    query: str,
    answer: str,
    selected_texts: list[str],
    merged_texts: list[str],
    must_contain: list[str],
    must_not: list[str],
) -> dict[str, bool | None]:
    """
    Definition funnel metrics for definition_queries category.

    - definition_retrieved: authoritative chunk appears in merged retrieval pool
    - definition_selected: authoritative chunk in final top-k context
    - definition_used: answer reflects authoritative content / must_contain terms
    - definition_correct: must_contain satisfied without must_not violations
    """
    entities = extract_register_entities(query)
    if not entities:
        return {
            "definition_retrieved": None,
            "definition_selected": None,
            "definition_used": None,
            "definition_correct": None,
        }

    def _has_auth(texts: list[str]) -> bool:
        return any(is_authoritative_definition(text, entity) for text in texts for entity in entities)

    retrieved = _has_auth(merged_texts) if merged_texts else _has_auth(selected_texts)
    selected = _has_auth(selected_texts)

    answer_l = answer.lower()
    used = False
    if selected:
        for text in selected_texts:
            if not any(is_authoritative_definition(text, e) for e in entities):
                continue
            auth_tokens = set(re.findall(r"[a-z0-9]{4,}", text.lower()))
            if auth_tokens and len(auth_tokens & set(re.findall(r"[a-z0-9]{4,}", answer_l))) >= 3:
                used = True
                break
    if not used and must_contain:
        used = all(term.lower() in answer_l for term in must_contain)

    correct = (
        bool(must_contain)
        and all(term.lower() in answer_l for term in must_contain)
        and not any(term.lower() in answer_l for term in must_not)
        and not is_abstention(answer)
    )

    return {
        "definition_retrieved": retrieved,
        "definition_selected": selected,
        "definition_used": used,
        "definition_correct": correct,
    }


def compute_case_metrics(
    *,
    query: str,
    answer: str,
    retrieved_texts: list[str],
    expected: dict[str, Any],
    expected_chunks: list[str],
    should_abstain: bool,
    expected_ordered_steps: list[str] | None,
    category: str,
    verification: dict[str, Any] | None,
    gated: bool,
    has_sources: bool,
    k: int,
    latency: LatencyMetrics,
    merged_retrieved_texts: list[str] | None = None,
) -> CaseMetrics:
    must_contain = expected.get("must_contain", [])
    must_not = expected.get("must_not_contain", [])

    recall = retrieval_recall_at_k(retrieved_texts, expected_chunks, k)
    mrr_val = mrr(retrieved_texts, expected_chunks)
    ndcg = ndcg_at_k(retrieved_texts, expected_chunks, k)

    mc_score = must_contain_score(answer, must_contain)
    violations = must_not_violations(answer, must_not)
    abstained = is_abstention(answer, gated=gated)

    unsupported_ratio = 0.0
    if verification:
        unsupported_ratio = float(verification.get("unsupported_ratio", 0.0) or 0.0)

    hallucination = violations > 0 or unsupported_ratio > 0.0 or (
        not should_abstain and must_contain and mc_score < 0.5 and not abstained
    )

    abstention_correct: bool | None = None
    if should_abstain:
        abstention_correct = abstained
    elif abstained:
        abstention_correct = False

    def_acc: float | None = None
    def_funnel: dict[str, bool | None] = {
        "definition_retrieved": None,
        "definition_selected": None,
        "definition_used": None,
        "definition_correct": None,
    }
    if category == "definition_queries":
        def_acc = mc_score if violations == 0 else 0.0
        merged = merged_retrieved_texts or retrieved_texts
        def_funnel = compute_definition_funnel(
            query=query,
            answer=answer,
            selected_texts=retrieved_texts,
            merged_texts=merged,
            must_contain=must_contain,
            must_not=must_not,
        )
        if def_funnel.get("definition_correct") is not None:
            def_acc = 1.0 if def_funnel["definition_correct"] else 0.0

    step_acc: float | None = None
    ordered_acc: float | None = None
    missing_rate: float | None = None
    extra_rate: float | None = None
    step_prec: float | None = None
    step_rec: float | None = None
    if expected_ordered_steps:
        step_acc = stepwise_accuracy(answer, expected_ordered_steps)
        ordered_acc = ordered_step_accuracy(answer, expected_ordered_steps)
        missing_rate = missing_step_rate(answer, expected_ordered_steps)
        extra_rate = extra_step_rate(answer, expected_ordered_steps)
        step_prec = step_precision(answer, expected_ordered_steps)
        step_rec = step_recall(answer, expected_ordered_steps)

    chunks_hit = sum(
        1
        for pattern in expected_chunks
        if any(chunk_matches_pattern(t, pattern) for t in retrieved_texts[:k])
    )

    num_sources = len(retrieved_texts)
    cite_cov = citation_coverage_per_sentence(answer)

    return CaseMetrics(
        retrieval_recall_at_k=recall,
        mrr=mrr_val,
        ndcg_at_k=ndcg,
        definition_accuracy=def_acc,
        hallucination=hallucination,
        unsupported_claim_ratio=unsupported_ratio,
        abstained=abstained,
        abstention_correct=abstention_correct,
        stepwise_accuracy=step_acc,
        ordered_step_accuracy=ordered_acc,
        missing_step_rate=missing_rate,
        extra_step_rate=extra_rate,
        step_precision=step_prec,
        step_recall=step_rec,
        citation_accuracy=citation_accuracy(
            answer,
            should_abstain=should_abstain,
            has_sources=has_sources,
            num_sources=num_sources,
            retrieved_texts=retrieved_texts,
        ),
        citation_coverage_per_sentence=cite_cov,
        definition_retrieved=def_funnel.get("definition_retrieved"),
        definition_selected=def_funnel.get("definition_selected"),
        definition_used=def_funnel.get("definition_used"),
        definition_correct=def_funnel.get("definition_correct"),
        must_contain_score=mc_score,
        must_not_violations=violations,
        expected_chunks_hit=chunks_hit,
        expected_chunks_total=len(expected_chunks),
        latency=latency,
    )


def aggregate_metrics(case_results: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate per-case metric dicts into summary statistics."""
    if not case_results:
        return {}

    def avg(key: str) -> float:
        vals = [r[key] for r in case_results if r.get(key) is not None]
        return sum(vals) / len(vals) if vals else 0.0

    def rate(key: str) -> float:
        vals = [r[key] for r in case_results if key in r]
        return sum(1 for v in vals if v) / len(vals) if vals else 0.0

    abstention_cases = [r for r in case_results if r.get("should_abstain")]
    abstention_preds = [r for r in case_results if r.get("abstained")]
    should_abstain_ids = {r["id"] for r in abstention_cases}
    pred_abstain_ids = {r["id"] for r in abstention_preds}

    abstention_precision = (
        len(should_abstain_ids & pred_abstain_ids) / len(pred_abstain_ids)
        if pred_abstain_ids
        else 0.0
    )
    abstention_recall = (
        len(should_abstain_ids & pred_abstain_ids) / len(should_abstain_ids)
        if should_abstain_ids
        else 0.0
    )

    return {
        "retrieval_recall_at_k": avg("retrieval_recall_at_k"),
        "mrr": avg("mrr"),
        "ndcg_at_k": avg("ndcg_at_k"),
        "definition_accuracy": avg("definition_accuracy"),
        "hallucination_rate": rate("hallucination"),
        "unsupported_claim_ratio": avg("unsupported_claim_ratio"),
        "abstention_precision": abstention_precision,
        "abstention_recall": abstention_recall,
        "stepwise_accuracy": avg("stepwise_accuracy"),
        "ordered_step_accuracy": avg("ordered_step_accuracy"),
        "missing_step_rate": avg("missing_step_rate"),
        "extra_step_rate": avg("extra_step_rate"),
        "step_precision": avg("step_precision"),
        "step_recall": avg("step_recall"),
        "citation_accuracy": avg("citation_accuracy"),
        "citation_coverage_per_sentence": avg("citation_coverage_per_sentence"),
        "definition_retrieved_rate": rate("definition_retrieved"),
        "definition_selected_rate": rate("definition_selected"),
        "definition_used_rate": rate("definition_used"),
        "definition_correct_rate": rate("definition_correct"),
        "must_contain_score": avg("must_contain_score"),
        "retrieval_ms": avg("retrieval_ms"),
        "rerank_ms": avg("rerank_ms"),
        "generation_ms": avg("generation_ms"),
        "verification_ms": avg("verification_ms"),
        "total_ms": avg("total_ms"),
    }


def aggregate_by_category(
    case_results: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for row in case_results:
        by_cat.setdefault(row.get("category", "unknown"), []).append(row)
    return {cat: aggregate_metrics(rows) for cat, rows in by_cat.items()}
