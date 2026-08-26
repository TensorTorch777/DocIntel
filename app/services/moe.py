"""Mixture-of-Experts gating for query + media routing.

Sparse top-k softmax gate (Switch-Transformer style) over specialized
experts. Logits are feature-based (intent, modality, lexical cues) so the
router is deterministic, testable, and does not require a trained gate.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum

from app.services.query_intent import QueryIntent, classify_query_intent


class ExpertId(str, Enum):
    RETRIEVAL = "retrieval"
    DEFINITION = "definition"
    VERIFICATION = "verification"
    PROCEDURAL = "procedural"
    VISION = "vision"
    AUDIO = "audio"
    VIDEO = "video"


EXPERT_LABELS: dict[ExpertId, str] = {
    ExpertId.RETRIEVAL: "Hybrid retrieval expert",
    ExpertId.DEFINITION: "Definition pinning expert",
    ExpertId.VERIFICATION: "Claim verification expert",
    ExpertId.PROCEDURAL: "Procedural extraction expert",
    ExpertId.VISION: "Vision / OCR expert",
    ExpertId.AUDIO: "Audio transcription expert",
    ExpertId.VIDEO: "Video keyframe + audio expert",
}

ALL_EXPERTS: tuple[ExpertId, ...] = tuple(ExpertId)

_VISION_CUES = re.compile(
    r"\b(image|screenshot|photo|figure|diagram|scan|ocr|picture|looks like)\b",
    re.I,
)
_AUDIO_CUES = re.compile(
    r"\b(voice|audio|recording|transcript|said|spoken|listen)\b",
    re.I,
)
_VIDEO_CUES = re.compile(
    r"\b(video|clip|recording|footage|frame|watch)\b",
    re.I,
)


@dataclass(frozen=True)
class ExpertWeight:
    expert: ExpertId
    weight: float
    label: str


@dataclass(frozen=True)
class MoEDecision:
    """Gating result used by retrieval, generation, and the live pipeline UI."""

    primary: ExpertId
    experts: tuple[ExpertWeight, ...]
    top_k: int
    media_kind: str
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "primary": self.primary.value,
            "top_k": self.top_k,
            "media_kind": self.media_kind,
            "reasons": list(self.reasons),
            "experts": [
                {"expert": e.expert.value, "weight": round(e.weight, 4), "label": e.label}
                for e in self.experts
            ],
        }

    @property
    def uses_vision(self) -> bool:
        return any(e.expert == ExpertId.VISION and e.weight >= 0.15 for e in self.experts)

    @property
    def uses_audio(self) -> bool:
        return any(e.expert == ExpertId.AUDIO and e.weight >= 0.15 for e in self.experts)

    @property
    def uses_video(self) -> bool:
        return any(e.expert == ExpertId.VIDEO and e.weight >= 0.15 for e in self.experts)


def _softmax(logits: dict[ExpertId, float]) -> dict[ExpertId, float]:
    peak = max(logits.values())
    exps = {k: math.exp(v - peak) for k, v in logits.items()}
    total = sum(exps.values()) or 1.0
    return {k: v / total for k, v in exps.items()}


def _base_logits() -> dict[ExpertId, float]:
    # Small positive prior on retrieval so text RAG remains the default expert.
    logits = {expert: -1.5 for expert in ALL_EXPERTS}
    logits[ExpertId.RETRIEVAL] = 1.2
    return logits


def route_experts(
    query: str,
    *,
    media_kind: str = "pdf",
    has_attachment: bool = False,
    intent: QueryIntent | str | None = None,
    top_k: int = 2,
) -> MoEDecision:
    """Compute sparse expert weights for a query and optional media."""
    reasons: list[str] = []
    logits = _base_logits()
    kind = (media_kind or "pdf").lower().strip()
    if kind in {"text", "document", ""}:
        kind = "pdf"

    if intent is None:
        intent = classify_query_intent(query).intent
    elif isinstance(intent, str):
        intent = QueryIntent(intent)

    if intent == QueryIntent.VERIFICATION:
        logits[ExpertId.VERIFICATION] += 3.4
        reasons.append("verification intent → verification expert")
    elif intent == QueryIntent.DEFINITION:
        logits[ExpertId.DEFINITION] += 3.2
        reasons.append("definition intent → definition expert")
    elif intent == QueryIntent.PROCEDURAL:
        logits[ExpertId.PROCEDURAL] += 3.2
        reasons.append("procedural intent → procedural expert")
    elif intent == QueryIntent.COMPARISON:
        logits[ExpertId.DEFINITION] += 2.4
        logits[ExpertId.RETRIEVAL] += 0.8
        reasons.append("comparison intent → definition + retrieval")
    elif intent == QueryIntent.LOOKUP:
        logits[ExpertId.RETRIEVAL] += 1.4
        logits[ExpertId.DEFINITION] += 0.8
        reasons.append("lookup intent → retrieval expert")

    if kind == "image" or (has_attachment and kind == "image"):
        logits[ExpertId.VISION] += 4.0
        logits[ExpertId.RETRIEVAL] += 0.4
        reasons.append("image modality → vision expert")
    elif kind == "audio":
        logits[ExpertId.AUDIO] += 4.0
        logits[ExpertId.RETRIEVAL] += 0.3
        reasons.append("audio modality → audio expert")
    elif kind == "video":
        logits[ExpertId.VIDEO] += 4.0
        logits[ExpertId.VISION] += 1.6
        logits[ExpertId.AUDIO] += 1.2
        reasons.append("video modality → video + vision/audio experts")

    if _VISION_CUES.search(query):
        logits[ExpertId.VISION] += 1.5
        reasons.append("visual language in query")
    if _AUDIO_CUES.search(query):
        logits[ExpertId.AUDIO] += 1.2
        reasons.append("audio language in query")
    if _VIDEO_CUES.search(query):
        logits[ExpertId.VIDEO] += 1.2
        reasons.append("video language in query")

    if has_attachment and kind in {"image", "audio", "video"}:
        logits[ExpertId.RETRIEVAL] += 0.6
        reasons.append("chat attachment fused into retrieval context")

    weights = _softmax(logits)
    ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    k = max(1, min(top_k, len(ranked)))
    selected = ranked[:k]
    experts = tuple(
        ExpertWeight(expert=eid, weight=w, label=EXPERT_LABELS[eid])
        for eid, w in selected
    )
    return MoEDecision(
        primary=experts[0].expert,
        experts=experts,
        top_k=k,
        media_kind=kind,
        reasons=tuple(reasons) or ("default retrieval prior",),
    )
