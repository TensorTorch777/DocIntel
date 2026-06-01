"""Query intent classification for routing, evidence gating, and answer templates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from app.services.query_preprocess import extract_core_query

# ---------------------------------------------------------------------------
# Intent taxonomy
# ---------------------------------------------------------------------------


class QueryIntent(str, Enum):
    DEFINITION = "definition"
    COMPARISON = "comparison"
    VERIFICATION = "verification"
    LOOKUP = "lookup"
    PROCEDURAL = "procedural"
    GENERAL = "general"


class AnswerTemplate(str, Enum):
    QA = "qa"
    VERIFICATION = "verification"
    COMPARISON = "comparison"
    PROCEDURAL = "procedural"
    CONSERVATIVE_QA = "conservative_qa"


class PipelineMode(str, Enum):
    STANDARD_QA = "standard_qa"
    VERIFICATION_QA = "verification_qa"
    COMPARISON_QA = "comparison_qa"
    PROCEDURAL_EXTRACTION = "procedural_extraction"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


# Evidence category labels (aligned with evidence_sufficiency + procedural)
EVIDENCE_DEFINITION = "definition"
EVIDENCE_BEHAVIOR = "behavior"
EVIDENCE_EXCEPTIONS = "exceptions"
EVIDENCE_INTERACTIONS = "interactions"
EVIDENCE_PROCEDURAL = "procedural"


_VERIFICATION_QUERY = re.compile(
    r"\b("
    r"is this (?:correct|right|true)|"
    r"is that (?:correct|right|true)|"
    r"am i (?:correct|right)|"
    r"verify(?:ing)? (?:that|whether)|"
    r"true or false|"
    r"correct\?\s*$"
    r")\b",
    re.I | re.M,
)
# User asserts a meaning then asks for validation: "X means Y. Is this correct?"
_VERIFICATION_MEANS_CLAIM = re.compile(
    r"\bmeans\b.+\?\s*$",
    re.I | re.S,
)

_COMPARISON_QUERY = re.compile(
    r"\b(compare|contrast|differentiate|difference between|vs\.?|versus|distinguish)\b",
    re.I,
)

_PROCEDURAL_STRONG = re.compile(
    r"\b("
    r"sequence|steps?|step-by-step|step by step|"
    r"process(?:\s+to|\s+for|\s+of|\s+required)?|"
    r"transition(?:\s+from|\s+to|\s+into|\s+between)?|"
    r"how\s+to|procedure|ordered(?:\s+steps|\s+sequence)?|"
    r"list\s+the(?:\s+sequence|\s+steps)?|must\s+first|happens\s+on|"
    r"what\s+(?:are\s+the\s+)?steps|walk\s+through|in\s+what\s+order"
    r")\b",
    re.I,
)

# Imperative procedural phrases — not bare "enable" in a definition claim
_PROCEDURAL_PHRASE = re.compile(
    r"\b("
    r"enable\s+paging|turn\s+on\s+paging|activate\s+paging|"
    r"enter\s+(?:protected|long|ia-32e|64-bit)\s+mode|"
    r"switch\s+(?:to|into)|configure\s+(?:the\s+)?(?:gdt|idt|paging)|"
    r"load\s+(?:gdt|idt|gdtr|idtr)|initialize\s+(?:paging|protected)"
    r")\b",
    re.I,
)

_DEFINITION_QUERY = re.compile(
    r"\b("
    r"what is|what are|define|definition of|meaning of|"
    r"which bit|bit number|bit position|register meaning|"
    r"explain what|describe what"
    r")\b",
    re.I,
)

# "Explain the sequence..." is procedural, not definition — handled by priority

_LOOKUP_QUERY = re.compile(
    r"\b("
    r"what is the (?:value|address|size|width)|"
    r"where is|how many bits|default value"
    r")\b",
    re.I,
)

_HALLUCINATION_BAIT = re.compile(
    r"\b(cause|causes|always|never|guarantee|#GP|#PF|without exception)\b",
    re.I,
)

# Yes/no entity-attribution or role questions (not only explicit "is this correct")
_YES_NO_ENTITY_QUERY = re.compile(
    r"^\s*(?:does|do|is|are|can|could|will|would)\s+"
    r"(?:the\s+)?(?:CR[0-8]|IA32_[A-Z0-9_]+|#(?:PF|GP|DF|NP|TS|SS|AC|MC|XM|VE|CP))\b",
    re.I,
)


@dataclass(frozen=True)
class QueryIntentResult:
    """Classification output used by retrieval, gating, and generation."""

    intent: QueryIntent
    pipeline: PipelineMode
    answer_template: AnswerTemplate
    evidence_categories: tuple[str, ...]
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "intent": self.intent.value,
            "pipeline": self.pipeline.value,
            "answer_template": self.answer_template.value,
            "evidence_categories": list(self.evidence_categories),
            "reasons": list(self.reasons),
        }


_INTENT_EVIDENCE: dict[QueryIntent, tuple[str, ...]] = {
    QueryIntent.DEFINITION: (EVIDENCE_DEFINITION,),
    QueryIntent.COMPARISON: (EVIDENCE_DEFINITION, EVIDENCE_BEHAVIOR),
    QueryIntent.VERIFICATION: (EVIDENCE_BEHAVIOR, EVIDENCE_EXCEPTIONS),
    QueryIntent.LOOKUP: (EVIDENCE_DEFINITION, EVIDENCE_BEHAVIOR),
    QueryIntent.PROCEDURAL: (EVIDENCE_PROCEDURAL, EVIDENCE_BEHAVIOR),
    QueryIntent.GENERAL: (EVIDENCE_BEHAVIOR,),
}

_INTENT_TEMPLATE: dict[QueryIntent, AnswerTemplate] = {
    QueryIntent.DEFINITION: AnswerTemplate.QA,
    QueryIntent.COMPARISON: AnswerTemplate.COMPARISON,
    QueryIntent.VERIFICATION: AnswerTemplate.VERIFICATION,
    QueryIntent.LOOKUP: AnswerTemplate.QA,
    QueryIntent.PROCEDURAL: AnswerTemplate.PROCEDURAL,
    QueryIntent.GENERAL: AnswerTemplate.QA,
}

_PIPELINE: dict[QueryIntent, PipelineMode] = {
    QueryIntent.DEFINITION: PipelineMode.STANDARD_QA,
    QueryIntent.COMPARISON: PipelineMode.COMPARISON_QA,
    QueryIntent.VERIFICATION: PipelineMode.VERIFICATION_QA,
    QueryIntent.LOOKUP: PipelineMode.STANDARD_QA,
    QueryIntent.PROCEDURAL: PipelineMode.PROCEDURAL_EXTRACTION,
    QueryIntent.GENERAL: PipelineMode.STANDARD_QA,
}


def _is_verification_query(query: str) -> bool:
    if _VERIFICATION_QUERY.search(query):
        return True
    if _VERIFICATION_MEANS_CLAIM.search(query.strip()):
        return True
    if _YES_NO_ENTITY_QUERY.search(extract_core_query(query)):
        return True
    return False


def _is_procedural_request(query: str) -> bool:
    """True when the user asks for steps/sequence — not when validating a definition."""
    if _is_verification_query(query):
        return False
    core = extract_core_query(query)
    if _PROCEDURAL_STRONG.search(core):
        return True
    if _PROCEDURAL_PHRASE.search(core):
        return True
    return False


def classify_query_intent(query: str) -> QueryIntentResult:
    """
    Classify query intent with explicit priority:

    verification > comparison > procedural > lookup > definition > general
    """
    core = extract_core_query(query)
    reasons: list[str] = []

    if _is_verification_query(query):
        reasons.append("validation phrasing (e.g. 'is this correct')")
        intent = QueryIntent.VERIFICATION
    elif _COMPARISON_QUERY.search(core):
        reasons.append("comparison/differentiation phrasing")
        intent = QueryIntent.COMPARISON
    elif _is_procedural_request(query):
        reasons.append("sequence/step/transition request")
        intent = QueryIntent.PROCEDURAL
    elif _LOOKUP_QUERY.search(core):
        reasons.append("factual lookup phrasing")
        intent = QueryIntent.LOOKUP
    elif _DEFINITION_QUERY.search(core):
        reasons.append("definition/explain-what phrasing")
        intent = QueryIntent.DEFINITION
    else:
        reasons.append("no specialized intent markers")
        intent = QueryIntent.GENERAL

    if _HALLUCINATION_BAIT.search(core) and intent == QueryIntent.GENERAL:
        reasons.append("exception/claim language — prefer conservative QA")
        intent = QueryIntent.VERIFICATION

    return QueryIntentResult(
        intent=intent,
        pipeline=_PIPELINE[intent],
        answer_template=_INTENT_TEMPLATE[intent],
        evidence_categories=_INTENT_EVIDENCE[intent],
        reasons=tuple(reasons),
    )


def is_procedural_intent(query: str) -> bool:
    """Whether the query should use the procedural extraction pipeline."""
    return classify_query_intent(query).intent == QueryIntent.PROCEDURAL


def required_evidence_categories(query: str) -> set[str]:
    """Intent-specific evidence categories for sufficiency gating."""
    return set(classify_query_intent(query).evidence_categories)
