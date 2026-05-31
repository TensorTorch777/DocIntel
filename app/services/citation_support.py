"""Claim extraction and citation-to-source alignment."""

from __future__ import annotations

import re

_CITATION_RE = re.compile(r"\[Source\s+(\d+)\]", re.I)
_ABSTAIN_PHRASES = re.compile(
    r"insufficient retrieved evidence|cannot answer from (the )?provided|not enough evidence",
    re.I,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_BULLET_LINE = re.compile(r"^\s*[-•*]\s+", re.MULTILINE)


_CLAIM_WITH_CITATION = re.compile(
    r"([^.!?]+[.!?])\s*(\[Source\s+\d+\])",
    re.I,
)


def extract_factual_sentences(answer: str) -> list[str]:
    """Split answer into claim-bearing sentences (skip abstention boilerplate)."""
    text = (answer or "").strip()
    if not text or _ABSTAIN_PHRASES.search(text):
        return []

    claims: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        if re.match(r"^Step\s+\d+\s*:", block, re.I):
            claims.append(block)
            continue

        for line in block.split("\n"):
            line = _BULLET_LINE.sub("", line).strip()
            if not line or len(line) < 12:
                continue
            if _ABSTAIN_PHRASES.search(line):
                continue

            consumed = 0
            for match in _CLAIM_WITH_CITATION.finditer(line):
                claims.append(f"{match.group(1).strip()} {match.group(2).strip()}")
                consumed = match.end()
            remainder = line[consumed:].strip()
            if remainder and len(remainder) >= 12:
                for part in _SENTENCE_SPLIT.split(remainder):
                    part = part.strip()
                    if part and len(part) >= 12 and not _ABSTAIN_PHRASES.search(part):
                        claims.append(part)

    return claims


def extract_cited_source_indices(text: str) -> list[int]:
    return [int(m.group(1)) for m in _CITATION_RE.finditer(text)]


def citation_coverage_per_sentence(answer: str) -> float:
    """Fraction of factual sentences that include at least one [Source N] citation."""
    claims = extract_factual_sentences(answer)
    if not claims:
        return 1.0
    cited = sum(1 for claim in claims if _CITATION_RE.search(claim))
    return cited / len(claims)


def citation_validity_score(answer: str, num_sources: int) -> float:
    """Fraction of citations that reference valid source indices (1..num_sources)."""
    if num_sources <= 0:
        return 0.0
    indices = extract_cited_source_indices(answer)
    if not indices:
        return 0.0
    valid = sum(1 for i in indices if 1 <= i <= num_sources)
    return valid / len(indices)


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", text.lower()))


def claim_supported_by_source(claim: str, source_text: str, *, min_overlap: float = 0.12) -> bool:
    """Lightweight lexical check: claim tokens overlap retrieved chunk."""
    claim_tokens = _token_set(re.sub(r"\[Source\s+\d+\]", "", claim, flags=re.I))
    if not claim_tokens:
        return False
    source_tokens = _token_set(source_text)
    if not source_tokens:
        return False
    overlap = len(claim_tokens & source_tokens) / len(claim_tokens)
    return overlap >= min_overlap


def claim_source_alignment(
    answer: str,
    retrieved_texts: list[str],
) -> float:
    """
    Fraction of cited claims whose referenced source(s) lexically support the claim.
    """
    claims = extract_factual_sentences(answer)
    if not claims:
        return 1.0

    scored = 0
    for claim in claims:
        indices = extract_cited_source_indices(claim)
        if not indices:
            continue
        claim_text = re.sub(r"\[Source\s+\d+\]", "", claim, flags=re.I)
        supported = any(
            1 <= idx <= len(retrieved_texts)
            and claim_supported_by_source(claim_text, retrieved_texts[idx - 1])
            for idx in indices
        )
        if supported:
            scored += 1

    cited_claims = sum(1 for c in claims if _CITATION_RE.search(c))
    if cited_claims == 0:
        return 0.0
    return scored / cited_claims


def citation_accuracy_score(
    answer: str,
    *,
    should_abstain: bool,
    has_sources: bool,
    num_sources: int,
    retrieved_texts: list[str] | None = None,
) -> float:
    """
    Combined citation metric: sentence coverage, valid indices, source alignment.
    """
    if should_abstain:
        count = len(_CITATION_RE.findall(answer))
        return 1.0 if count == 0 else max(0.0, 1.0 - count * 0.25)
    if not has_sources or num_sources <= 0:
        return 0.0

    coverage = citation_coverage_per_sentence(answer)
    validity = citation_validity_score(answer, num_sources)
    alignment = (
        claim_source_alignment(answer, retrieved_texts or [])
        if retrieved_texts
        else coverage
    )
    return min(1.0, 0.5 * coverage + 0.2 * validity + 0.3 * alignment)
