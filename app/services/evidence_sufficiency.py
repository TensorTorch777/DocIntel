"""Pre-generation evidence sufficiency and retrieval confidence scoring."""

import re
from dataclasses import dataclass, field

from app.services.definitional_boost import definitional_score, extract_target_entities
from app.services.entity_matcher import extract_entities
from app.services.query_preprocess import extract_core_query
from app.services.register_definition_resolver import (
    authoritative_coverage,
    extract_register_entities,
    is_authoritative_definition,
    requires_exact_definition,
)
from app.services.vector_store import RetrievedChunk

# Claim categories checked before generation
_CATEGORY_DEFINITION = "definition"
_CATEGORY_BEHAVIOR = "behavior"
_CATEGORY_EXCEPTIONS = "exceptions"
_CATEGORY_INTERACTIONS = "interactions"

_EXPLAIN_QUERY = re.compile(
    r"\b(explain|describe|what is|what are|define|definition of|meaning of|differentiate|compare|contrast)\b",
    re.I,
)
_BEHAVIOR_QUERY = re.compile(
    r"\b(behavior|behaviour|how does|how do|when set|when clear|effect of)\b",
    re.I,
)
_EXCEPTION_QUERY = re.compile(
    r"\b(exception|#(?:PF|GP|DF|NP|TS|SS|AC|MC|XM|VE|CP)|fault|trap)\b",
    re.I,
)
_INTERACTION_QUERY = re.compile(
    r"\b(interact|interaction|paging|page table|when used with|depends on|requires)\b",
    re.I,
)

_DEFINITION_EVIDENCE = (
    re.compile(r"\bdefined as\b", re.I),
    re.compile(r"\bmeans\b", re.I),
    re.compile(r"\bflag\b", re.I),
    re.compile(r"\bbit\s+\d+\b", re.I),
    re.compile(r"\(bit\s+\d+", re.I),
    re.compile(r"—"),
    re.compile(r"\bglossary\b", re.I),
    re.compile(r"\bpaging\s*\(", re.I),
)
_BEHAVIOR_EVIDENCE = (
    re.compile(r"\bwhen set\b", re.I),
    re.compile(r"\bwhen clear\b", re.I),
    re.compile(r"\benables?\b", re.I),
    re.compile(r"\bdisables?\b", re.I),
    re.compile(r"\bif .{0,40} set\b", re.I),
    re.compile(r"\bcauses?\b", re.I),
)
_EXCEPTION_EVIDENCE = (
    re.compile(r"#(?:PF|GP|DF|NP|TS|SS|AC|MC|XM|VE|CP)\b", re.I),
    re.compile(r"\bgenerates? (?:a |an )?(?:#|general protection|page fault)", re.I),
    re.compile(r"\bexception\b", re.I),
)
_INTERACTION_EVIDENCE = (
    re.compile(r"\bpaging\b", re.I),
    re.compile(r"\bpage table\b", re.I),
    re.compile(r"\bCR[0-8]\b", re.I),
    re.compile(r"\bwhen used with\b", re.I),
    re.compile(r"\brequires\b", re.I),
)


@dataclass
class CategoryCoverage:
    """Whether retrieved chunks explicitly support a claim category."""

    definition: bool = False
    behavior: bool = False
    exceptions: bool = False
    interactions: bool = False
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "definition": self.definition,
            "behavior": self.behavior,
            "exceptions": self.exceptions,
            "interactions": self.interactions,
            "missing_categories": self.missing,
        }


@dataclass
class SufficiencyResult:
    """Pre-generation gate decision."""

    sufficient: bool
    confidence: str  # high | medium | low
    coverage: CategoryCoverage
    message: str | None = None
    entity_mentions: int = 0
    definitional_hits: int = 0
    top_rerank_score: float = 0.0
    authoritative_definitions_found: bool = False
    missing_definition_entities: list[str] = field(default_factory=list)
    pinned_chunk_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sufficient": self.sufficient,
            "confidence": self.confidence,
            "coverage": self.coverage.to_dict(),
            "message": self.message,
            "entity_mentions": self.entity_mentions,
            "definitional_hits": self.definitional_hits,
            "top_rerank_score": self.top_rerank_score,
            "authoritative_definitions_found": self.authoritative_definitions_found,
            "missing_definition_entities": self.missing_definition_entities,
            "pinned_chunk_ids": self.pinned_chunk_ids,
        }


def _entity_in_text(text: str, target: str) -> bool:
    upper = text.upper()
    if target in upper:
        return True
    if "." in target:
        bit = target.split(".", 1)[1]
        return bit in upper
    return False


def _chunk_mentions_entity(text: str, targets: tuple[str, ...]) -> bool:
    return any(_entity_in_text(text, t) for t in targets)


def _category_supported(
    chunks: list[RetrievedChunk],
    targets: tuple[str, ...],
    patterns: tuple[re.Pattern[str], ...],
) -> bool:
    for chunk in chunks:
        if not _chunk_mentions_entity(chunk.text, targets):
            continue
        if any(p.search(chunk.text) for p in patterns):
            return True
    return False


def _required_categories(query: str) -> set[str]:
    core = extract_core_query(query)
    required: set[str] = set()

    if _EXPLAIN_QUERY.search(core):
        required.add(_CATEGORY_DEFINITION)
    if _BEHAVIOR_QUERY.search(core):
        required.add(_CATEGORY_BEHAVIOR)
    if _EXCEPTION_QUERY.search(core):
        required.add(_CATEGORY_EXCEPTIONS)
    if _INTERACTION_QUERY.search(core):
        required.add(_CATEGORY_INTERACTIONS)

    # Broad explain queries need at least definition evidence
    if not required and re.search(r"\b(flag|bit|register|msr)\b", core, re.I):
        required.add(_CATEGORY_DEFINITION)

    return required


def measure_coverage(
    chunks: list[RetrievedChunk],
    query: str,
) -> CategoryCoverage:
    """Check which claim categories are explicitly supported by retrieval."""
    targets = extract_register_entities(query) or extract_target_entities(query)
    entities = extract_entities(extract_core_query(query))
    if not targets:
        targets = tuple(entities.registers + entities.flags)

    coverage = CategoryCoverage(
        definition=any(is_authoritative_definition(c.text, t) for c in chunks for t in targets)
        if targets
        else bool(chunks),
        behavior=_category_supported(chunks, targets, _BEHAVIOR_EVIDENCE),
        exceptions=_category_supported(chunks, targets, _EXCEPTION_EVIDENCE),
        interactions=_category_supported(chunks, targets, _INTERACTION_EVIDENCE),
    )

    required = _required_categories(query)
    checks = {
        _CATEGORY_DEFINITION: coverage.definition,
        _CATEGORY_BEHAVIOR: coverage.behavior,
        _CATEGORY_EXCEPTIONS: coverage.exceptions,
        _CATEGORY_INTERACTIONS: coverage.interactions,
    }
    coverage.missing = [cat for cat in required if not checks.get(cat, False)]
    return coverage


def compute_retrieval_confidence(
    chunks: list[RetrievedChunk],
    coverage: CategoryCoverage,
    query: str,
) -> str:
    """Classify retrieval confidence as high, medium, or low."""
    if not chunks:
        return "low"

    targets = extract_target_entities(query)
    top_rerank = max(
        float(c.metadata.get("rerank_score", c.score)) for c in chunks
    )
    entity_mentions = sum(
        1 for c in chunks if _chunk_mentions_entity(c.text, targets)
    ) if targets else len(chunks)
    def_hits = sum(definitional_score(c.text, targets) for c in chunks) if targets else 0

    rerank_scores = [
        float(c.metadata.get("rerank_score", c.score)) for c in chunks[:3]
    ]
    score_spread = max(rerank_scores) - min(rerank_scores) if rerank_scores else 1.0

    if (
        coverage.definition
        and top_rerank >= 0.35
        and entity_mentions >= 1
        and def_hits >= 2
        and score_spread <= 0.25
    ):
        return "high"

    if entity_mentions >= 1 and (coverage.definition or top_rerank >= 0.25):
        return "medium"

    return "low"


def build_insufficient_message(
    query: str,
    coverage: CategoryCoverage,
    confidence: str,
    missing_definition_entities: list[str] | None = None,
) -> str:
    """Human-readable insufficient-evidence response."""
    targets = extract_register_entities(query) or extract_target_entities(query)
    entity_label = ", ".join(targets) if targets else "the requested topic"

    if missing_definition_entities:
        missing = ", ".join(missing_definition_entities)
        return (
            f"Insufficient retrieved evidence for exact register definition "
            f"({missing})."
        )

    if requires_exact_definition(query) and not coverage.definition:
        return "Insufficient retrieved evidence for exact register definition."

    if confidence == "low" and not coverage.definition:
        return (
            f"Retrieved context mentions {entity_label} but does not provide "
            f"sufficient detail regarding semantics or exceptions."
        )

    if coverage.missing:
        missing = ", ".join(coverage.missing)
        return (
            f"Retrieved context mentions {entity_label} but lacks explicit evidence "
            f"for: {missing}. Cannot answer without inference."
        )

    return "Insufficient retrieved evidence."


def assess_sufficiency(
    chunks: list[RetrievedChunk],
    query: str,
    pinned_chunk_ids: list[str] | None = None,
) -> SufficiencyResult:
    """Decide whether retrieved evidence is sufficient to generate an answer."""
    coverage = measure_coverage(chunks, query)
    confidence = compute_retrieval_confidence(chunks, coverage, query)
    targets = extract_register_entities(query) or extract_target_entities(query)

    all_covered, missing_defs = authoritative_coverage(chunks, query)
    entity_mentions = sum(
        1 for c in chunks if _chunk_mentions_entity(c.text, targets)
    ) if targets else len(chunks)
    def_hits = sum(definitional_score(c.text, targets) for c in chunks) if targets else 0
    top_rerank = max(
        (float(c.metadata.get("rerank_score", c.score)) for c in chunks),
        default=0.0,
    )

    required = _required_categories(query)
    sufficient = len(coverage.missing) == 0

    if requires_exact_definition(query) and not all_covered:
        sufficient = False
        confidence = "low"
        coverage.definition = False
        if "definition" not in coverage.missing:
            coverage.missing.append("definition")

    # Low confidence with only passing mentions → gate
    if confidence == "low" and targets and entity_mentions > 0 and def_hits < 2:
        sufficient = False

    # Explain query without definition evidence → gate
    if _CATEGORY_DEFINITION in required and not coverage.definition:
        sufficient = False
        confidence = "low"

    message = None
    if not sufficient:
        message = build_insufficient_message(
            query, coverage, confidence, missing_defs if missing_defs else None
        )

    return SufficiencyResult(
        sufficient=sufficient,
        confidence=confidence,
        coverage=coverage,
        message=message,
        entity_mentions=entity_mentions,
        definitional_hits=def_hits,
        top_rerank_score=top_rerank,
        authoritative_definitions_found=all_covered,
        missing_definition_entities=missing_defs,
        pinned_chunk_ids=pinned_chunk_ids or [],
    )
