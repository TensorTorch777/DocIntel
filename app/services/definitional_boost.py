"""Boost retrieval toward definitional/glossary chunks for register/flag queries."""

import re

from app.services.register_definition_resolver import (
    authoritative_definition_score,
    extract_register_entities,
)
from app.services.vector_store import RetrievedChunk

# Re-export for backward compatibility
extract_target_entities = extract_register_entities

_DEFINITION_SIGNALS = (
    re.compile(r"\bdefined as\b", re.I),
    re.compile(r"\bmeans\b", re.I),
    re.compile(r"\bis the\b", re.I),
    re.compile(r"\bflag\b", re.I),
    re.compile(r"\bbit\s+\d+\b", re.I),
    re.compile(r"\(bit\s+\d+", re.I),
    re.compile(r"[—–-]"),
    re.compile(r"\bglossary\b", re.I),
    re.compile(r"\bdescription\b", re.I),
    re.compile(r"\bpaging\s*\(", re.I),
)


def definitional_score(text: str, targets: tuple[str, ...]) -> int:
    """Score how definitional a chunk is (delegates to authoritative scorer)."""
    if not targets:
        return 0
    return max(authoritative_definition_score(text, t) for t in targets)


def apply_definitional_boost(
    chunks: list[RetrievedChunk],
    query: str,
    boost_weight: float = 0.12,
) -> list[RetrievedChunk]:
    """Boost chunks that define requested register/flag entities."""
    targets = extract_target_entities(query)
    if not targets:
        return chunks

    boosted: list[RetrievedChunk] = []
    for chunk in chunks:
        d_score = definitional_score(chunk.text, targets)
        meta = dict(chunk.metadata)
        meta["definitional_score"] = d_score
        boost = d_score * boost_weight
        meta["definitional_boost"] = boost
        boosted.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                score=chunk.score + boost,
                metadata=meta,
            )
        )

    boosted.sort(key=lambda c: c.score, reverse=True)
    return boosted
