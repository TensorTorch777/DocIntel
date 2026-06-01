"""Pre-generation evidence sufficiency and retrieval confidence scoring."""

import re
from dataclasses import dataclass, field

from app.config import get_settings
from app.services.claim_refutation import ClaimRefutation, detect_claim_refutation
from app.services.definitional_boost import definitional_score, extract_target_entities
from app.services.entity_matcher import extract_entities
from app.services.query_preprocess import extract_core_query
from app.services.query_intent import (
    EVIDENCE_PROCEDURAL,
    QueryIntent,
    classify_query_intent,
)
from app.services.register_definition_resolver import (
    authoritative_coverage,
    extract_register_entities,
    is_authoritative_definition,
    requires_exact_definition,
)
from app.services.vector_store import RetrievedChunk

# Default weighted coverage model (overridden by Settings / .env)
COVERAGE_WEIGHTS: dict[str, float] = {
    "definition": 0.35,
    "behavior": 0.25,
    "exceptions": 0.20,
    "interactions": 0.20,
}

CONFIDENCE_HIGH_THRESHOLD = 0.80
CONFIDENCE_MEDIUM_THRESHOLD = 0.50


def _coverage_weights() -> dict[str, float]:
    s = get_settings()
    return {
        "definition": s.coverage_weight_definition,
        "behavior": s.coverage_weight_behavior,
        "exceptions": s.coverage_weight_exceptions,
        "interactions": s.coverage_weight_interactions,
    }


def _confidence_high_threshold() -> float:
    return get_settings().coverage_confidence_high


def _confidence_medium_threshold() -> float:
    return get_settings().coverage_confidence_medium

_QUERY_STOPWORDS = frozenset(
    {
        "what", "how", "does", "the", "and", "for", "with", "from", "that", "this",
        "are", "is", "of", "in", "to", "a", "an", "on", "or", "be", "by", "at",
        "explain", "describe", "define", "list", "which", "when", "where", "why",
        "work", "works", "using", "use", "about", "detail", "details", "example",
    }
)

_CATEGORY_DEFINITION = "definition"
_CATEGORY_BEHAVIOR = "behavior"
_CATEGORY_EXCEPTIONS = "exceptions"
_CATEGORY_INTERACTIONS = "interactions"
_CATEGORY_PROCEDURAL = EVIDENCE_PROCEDURAL

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
_BIT_NUMBER_QUERY = re.compile(
    r"\b(bit\s+(?:number|position|field)|which\s+bit|bit\s+\d+)\b",
    re.I,
)
_REGISTER_MEANING_QUERY = re.compile(
    r"\b(register\s+meaning|meaning\s+of|what\s+does\s+(?:CR|IA32|EFER|RFLAGS))",
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
_PROCEDURAL_EVIDENCE = (
    re.compile(r"\bsequence\b", re.I),
    re.compile(r"\bsteps?\b", re.I),
    re.compile(r"\bfirst\b", re.I),
    re.compile(r"\bthen\b", re.I),
    re.compile(r"\bmust\b", re.I),
    re.compile(r"\bbefore\b", re.I),
    re.compile(r"\bafter\b", re.I),
    re.compile(r"\btransition\b", re.I),
    re.compile(r"\benter(?:ing)?\b", re.I),
    re.compile(r"\bmode\b", re.I),
    re.compile(r"\bLGDT\b", re.I),
    re.compile(r"\bLIDT\b", re.I),
    re.compile(r"\bfar jump\b", re.I),
)


@dataclass
class CategoryCoverage:
    """Per-category evidence scores (0.0–1.0) and legacy boolean flags."""

    definition: float = 0.0
    behavior: float = 0.0
    exceptions: float = 0.0
    interactions: float = 0.0
    procedural: float = 0.0
    query_relevance: float = 0.0
    total_weighted: float = 0.0
    missing: list[str] = field(default_factory=list)

    @property
    def definition_met(self) -> bool:
        return self.definition >= 0.5

    @property
    def behavior_met(self) -> bool:
        return self.behavior >= 0.5

    @property
    def exceptions_met(self) -> bool:
        return self.exceptions >= 0.5

    @property
    def interactions_met(self) -> bool:
        return self.interactions >= 0.5

    @property
    def procedural_met(self) -> bool:
        return self.procedural >= 0.5

    def to_dict(self) -> dict:
        return {
            "definition": self.definition,
            "behavior": self.behavior,
            "exceptions": self.exceptions,
            "interactions": self.interactions,
            "procedural": self.procedural,
            "query_relevance": self.query_relevance,
            "total_weighted": self.total_weighted,
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
    coverage_score: float = 0.0
    refutation: ClaimRefutation | None = None

    def to_dict(self) -> dict:
        return {
            "sufficient": self.sufficient,
            "confidence": self.confidence,
            "coverage_score": self.coverage_score,
            "coverage": self.coverage.to_dict(),
            "message": self.message,
            "entity_mentions": self.entity_mentions,
            "definitional_hits": self.definitional_hits,
            "top_rerank_score": self.top_rerank_score,
            "authoritative_definitions_found": self.authoritative_definitions_found,
            "missing_definition_entities": self.missing_definition_entities,
            "pinned_chunk_ids": self.pinned_chunk_ids,
            "refutation": (
                {
                    "queried_entity": self.refutation.queried_entity,
                    "alternative_entity": self.refutation.alternative_entity,
                    "role": self.refutation.role,
                    "evidence_text": self.refutation.evidence_text,
                    "authoritative": self.refutation.authoritative,
                }
                if self.refutation
                else None
            ),
        }


def requires_authoritative_definition(query: str) -> bool:
    """Strict definition queries: exact meaning, bit number, or register semantics."""
    if requires_exact_definition(query):
        return True
    core = extract_core_query(query)
    if _BIT_NUMBER_QUERY.search(core):
        return True
    if _REGISTER_MEANING_QUERY.search(core):
        return True
    if extract_register_entities(query):
        return bool(_EXPLAIN_QUERY.search(core))
    return False


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


def _pattern_hits(text: str, patterns: tuple[re.Pattern[str], ...]) -> int:
    return sum(1 for p in patterns if p.search(text))


def _category_score(
    chunks: list[RetrievedChunk],
    targets: tuple[str, ...],
    patterns: tuple[re.Pattern[str], ...],
    *,
    authoritative: bool = False,
) -> float:
    """Score 0.0–1.0 for category support across retrieved chunks."""
    if not chunks:
        return 0.0

    best = 0.0
    for chunk in chunks:
        text = chunk.text
        entity_hit = _chunk_mentions_entity(text, targets) if targets else True
        if not entity_hit:
            continue

        if authoritative:
            if targets and any(is_authoritative_definition(text, t) for t in targets):
                return 1.0
            def_score = (
                max(
                    (definitional_score(text, targets) / 3.0 if targets else 0.0),
                    0.0,
                )
            )
            pattern_score = min(_pattern_hits(text, patterns) / 3.0, 1.0)
            chunk_score = max(def_score, pattern_score * 0.7)
        else:
            pattern_score = min(_pattern_hits(text, patterns) / 2.0, 1.0)
            mention_score = 0.25 if entity_hit else 0.0
            chunk_score = max(pattern_score, mention_score)

        best = max(best, min(chunk_score, 1.0))

    return best


def _extract_query_terms(query: str) -> list[str]:
    core = extract_core_query(query).lower()
    tokens = re.findall(r"[a-z0-9]{4,}", core)
    return [t for t in tokens if t not in _QUERY_STOPWORDS]


def _query_relevance_score(chunks: list[RetrievedChunk], query: str) -> float:
    """How well retrieved chunks cover query terms (for off-manual / general queries)."""
    terms = _extract_query_terms(query)
    if not terms or not chunks:
        return 0.0

    combined = " ".join(c.text.lower() for c in chunks[:5])
    hits = sum(1 for term in terms if term in combined)
    return min(hits / len(terms), 1.0)


def _required_categories(query: str) -> set[str]:
    """Intent-first category requirements; legacy regex fills gaps for exceptions."""
    intent_result = classify_query_intent(query)
    required = set(intent_result.evidence_categories)

    core = extract_core_query(query)
    if _EXCEPTION_QUERY.search(core):
        required.add(_CATEGORY_EXCEPTIONS)
    if _INTERACTION_QUERY.search(core) and intent_result.intent != QueryIntent.PROCEDURAL:
        required.add(_CATEGORY_INTERACTIONS)
    if _BEHAVIOR_QUERY.search(core) and _CATEGORY_BEHAVIOR not in required:
        required.add(_CATEGORY_BEHAVIOR)

    if not required and re.search(r"\b(flag|bit|register|msr)\b", core, re.I):
        required.add(_CATEGORY_DEFINITION)

    return required


def compute_weighted_coverage(
    scores: CategoryCoverage,
    required: set[str],
) -> float:
    """Weighted total over required categories; falls back to query relevance."""
    weights = dict(_coverage_weights())
    weights[_CATEGORY_PROCEDURAL] = 0.45

    if required:
        active = {cat: weights.get(cat, 0.25) for cat in required}
        if not active:
            return scores.query_relevance
        total_weight = sum(active.values())
        weighted = sum(
            active[cat] * getattr(
                scores,
                cat if cat != _CATEGORY_PROCEDURAL else "procedural",
            )
            for cat in active
        )
        return weighted / total_weight

    return scores.query_relevance


def confidence_from_coverage(coverage_score: float) -> str:
    high = _confidence_high_threshold()
    medium = _confidence_medium_threshold()
    if coverage_score > high:
        return "high"
    if coverage_score >= medium:
        return "medium"
    return "low"


def measure_coverage(
    chunks: list[RetrievedChunk],
    query: str,
) -> CategoryCoverage:
    """Compute per-category scores and weighted total coverage."""
    intent_result = classify_query_intent(query)
    targets = extract_register_entities(query) or extract_target_entities(query)
    entities = extract_entities(extract_core_query(query))
    if not targets:
        targets = tuple(entities.registers + entities.flags)

    # Verification/contradiction: score topic evidence, not only the queried entity
    score_targets = () if intent_result.intent == QueryIntent.VERIFICATION else targets

    coverage = CategoryCoverage(
        definition=_category_score(
            chunks, score_targets, _DEFINITION_EVIDENCE, authoritative=True
        ),
        behavior=_category_score(chunks, score_targets, _BEHAVIOR_EVIDENCE),
        exceptions=_category_score(chunks, score_targets, _EXCEPTION_EVIDENCE),
        interactions=_category_score(chunks, score_targets, _INTERACTION_EVIDENCE),
        procedural=_category_score(chunks, score_targets, _PROCEDURAL_EVIDENCE),
        query_relevance=_query_relevance_score(chunks, query),
    )

    required = _required_categories(query)
    checks = {
        _CATEGORY_DEFINITION: coverage.definition,
        _CATEGORY_BEHAVIOR: coverage.behavior,
        _CATEGORY_EXCEPTIONS: coverage.exceptions,
        _CATEGORY_INTERACTIONS: coverage.interactions,
        _CATEGORY_PROCEDURAL: coverage.procedural,
    }
    medium = _confidence_medium_threshold()
    coverage.missing = [
        cat for cat in required if checks.get(cat, 0.0) < medium
    ]
    coverage.total_weighted = compute_weighted_coverage(coverage, required)
    return coverage


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

    if requires_authoritative_definition(query) and coverage.definition < 0.5:
        return "Insufficient retrieved evidence for exact register definition."

    medium = _confidence_medium_threshold()
    if confidence == "low" and coverage.query_relevance < medium:
        return (
            "Insufficient retrieved evidence. Retrieved sources do not cover "
            "the topic of this question."
        )

    if confidence == "low" and targets and coverage.definition < medium:
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
    intent_result = classify_query_intent(query)
    coverage = measure_coverage(chunks, query)
    required = _required_categories(query)
    coverage_score = coverage.total_weighted
    confidence = confidence_from_coverage(coverage_score)

    targets = extract_register_entities(query) or extract_target_entities(query)
    all_covered, missing_defs = authoritative_coverage(chunks, query)
    entity_mentions = sum(
        1 for c in chunks if _chunk_mentions_entity(c.text, targets)
    ) if targets else 0
    def_hits = sum(definitional_score(c.text, targets) for c in chunks) if targets else 0
    top_rerank = max(
        (float(c.metadata.get("rerank_score", c.score)) for c in chunks),
        default=0.0,
    )

    # Boost score when pinned authoritative definitions are present
    if pinned_chunk_ids:
        coverage.definition = max(coverage.definition, 1.0)
        if _CATEGORY_DEFINITION in required:
            coverage.missing = [c for c in coverage.missing if c != _CATEGORY_DEFINITION]
        coverage_score = compute_weighted_coverage(coverage, required)
        confidence = confidence_from_coverage(coverage_score)

    medium = _confidence_medium_threshold()
    sufficient = coverage_score >= medium and not coverage.missing

    refutation = detect_claim_refutation(chunks, query)
    if refutation:
        sufficient = True
        confidence = "high"
        coverage.missing = []
        coverage_score = max(coverage_score, _confidence_high_threshold())
        coverage.total_weighted = coverage_score

    # Definition strictness: not for verification/refutation or procedural queries
    if (
        requires_authoritative_definition(query)
        and intent_result.intent not in (QueryIntent.PROCEDURAL, QueryIntent.VERIFICATION)
        and not refutation
    ):
        has_authoritative = all_covered or any(
            c.metadata.get("pinned_definition") for c in chunks
        )
        if not has_authoritative:
            sufficient = False
            confidence = "low"
            if "definition" not in coverage.missing:
                coverage.missing.append("definition")
            coverage.definition = min(coverage.definition, 0.49)

    # Low confidence → prefer abstention
    if confidence == "low":
        sufficient = False

    # Off-manual queries: low query relevance → abstain even if chunks exist
    if not required and not targets and coverage.query_relevance < medium:
        sufficient = False
        confidence = "low"

    message = None
    if not sufficient:
        message = build_insufficient_message(
            query,
            coverage,
            confidence,
            missing_defs if missing_defs and not refutation else None,
        )

    return SufficiencyResult(
        sufficient=sufficient,
        confidence=confidence,
        coverage=coverage,
        coverage_score=coverage_score,
        message=message,
        entity_mentions=entity_mentions,
        definitional_hits=def_hits,
        top_rerank_score=top_rerank,
        authoritative_definitions_found=all_covered or bool(pinned_chunk_ids),
        missing_definition_entities=missing_defs,
        pinned_chunk_ids=pinned_chunk_ids or [],
        refutation=refutation,
    )
