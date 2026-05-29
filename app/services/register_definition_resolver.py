"""Authoritative register/flag/exception definition resolution and pinning."""

import re
from dataclasses import dataclass

from app.services.query_preprocess import extract_core_query
from app.services.vector_store import RetrievedChunk

# Query entity patterns
_DOTTED_ENTITY = re.compile(
    r"\b(CR[0-8]\.[A-Z0-9]+|IA32_[A-Z0-9_]+(?:\.[A-Z0-9]+)?)\b",
    re.I,
)
_REGISTER = re.compile(r"\b(CR[0-8])\b", re.I)
_EXCEPTION = re.compile(r"#(?:PF|GP|DF|NP|TS|SS|AC|MC|XM|VE|CP)\b", re.I)
_NAMED_FLAG = re.compile(r"\b(NXE|PGE|PG|PE|PAE|LME|WP|SMEP|SMAP)\b", re.I)

# Authoritative definition signals
_BIT_OF_REGISTER = re.compile(r"\(bit\s+\d+\s+of\s+CR[0-8]\)", re.I)
_BRACKET_BIT = re.compile(r"\[bit\s+\d+\]", re.I)
_EM_DASH_DEF = re.compile(r"[—–-]\s*[A-Za-z]", re.I)
_BIT_NUMBER = re.compile(r"\bbit\s+\d+\b", re.I)
_FIGURE = re.compile(r"\bFigure\s+\d+", re.I)
_CONTAINS = re.compile(r"\bcontains\b", re.I)
_FLAG_WORD = re.compile(r"\bflag\b", re.I)

# Usage/procedural passages — not authoritative definitions
_USAGE_SIGNALS = (
    re.compile(r"\bwhen\s+(?:CR|the)\b", re.I),
    re.compile(r"\bif\s+.{0,40}\s+is\s+set\b", re.I),
    re.compile(r"\bmust\s+be\s+set\b", re.I),
    re.compile(r"\benabling\s+paging\b", re.I),
    re.compile(r"\bto\s+enter\b", re.I),
    re.compile(r"\bsequence\b", re.I),
)

# Known authoritative templates (Intel SDM style)
_ENTITY_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "CR0.PG": (
        re.compile(r"PG\s*[—–-]\s*Paging\s*\(bit\s+31\s+of\s+CR0\)", re.I),
        re.compile(r"Paging\s*\(bit\s+31\s+of\s+CR0\)", re.I),
        re.compile(r"CR0\.PG.*bit\s+31", re.I),
    ),
    "CR4.PGE": (
        re.compile(r"PGE\s*[—–-]\s*Page\s+Global\s+Enable", re.I),
        re.compile(r"Page\s+Global\s+Enable\s*\(bit\s+7\s+of\s+CR4\)", re.I),
        re.compile(r"Page\s+Global\s+Enable\s*\(bit\s+8\s+of\s+CR4\)", re.I),
        re.compile(r"CR4\.PGE.*bit\s+[78]", re.I),
        re.compile(r"PGE\s*\(page\s+global\s+enable\)", re.I),
    ),
    "IA32_EFER.NXE": (
        re.compile(r"IA32_EFER\.NXE\s*\[bit\s+11\]", re.I),
        re.compile(r"NXE\s*[—–-]\s*Execute\s+Disable\s+Enable", re.I),
        re.compile(r"Execute\s+Disable\s+Enable\s*\(bit\s+11", re.I),
    ),
    "CR2": (
        re.compile(r"CR2\s*[—–-]\s*Page-Fault\s+Linear\s+Address", re.I),
        re.compile(r"Page-Fault\s+Linear\s+Address\s*\(CR2\)", re.I),
    ),
    "CR3": (
        re.compile(r"CR3\s*[—–-]\s*Page-Directory\s+Base", re.I),
        re.compile(r"Page-Directory\s+Base\s+Register\s*\(CR3\)", re.I),
    ),
    "#PF": (
        re.compile(r"#PF\s*[—–-]\s*Page\s+Fault", re.I),
        re.compile(r"Page\s+Fault\s*\(#PF\)", re.I),
    ),
    "#GP": (
        re.compile(r"#GP\s*[—–-]\s*General\s+Protection", re.I),
        re.compile(r"General\s+Protection\s*\(#GP\)", re.I),
    ),
}

_AUTHORITATIVE_THRESHOLD = 8


@dataclass(frozen=True)
class DefinitionMatch:
    """A chunk matched as an authoritative entity definition."""

    entity: str
    chunk: RetrievedChunk
    score: int
    authoritative: bool


def extract_register_entities(query: str) -> tuple[str, ...]:
    """All technical entities requiring definition resolution."""
    core = extract_core_query(query)
    seen: set[str] = set()
    entities: list[str] = []

    for match in _DOTTED_ENTITY.findall(core):
        upper = match.upper()
        if upper not in seen:
            seen.add(upper)
            entities.append(upper)

    dotted_registers = {e.split(".", 1)[0] for e in entities if "." in e}

    for match in _REGISTER.findall(core):
        upper = match.upper()
        if upper in dotted_registers:
            continue
        if upper not in seen:
            seen.add(upper)
            entities.append(upper)

    for match in _EXCEPTION.findall(core):
        upper = match.upper()
        if upper not in seen:
            seen.add(upper)
            entities.append(upper)

    # Standalone flags only when not already covered by dotted form
    dotted_bits = {e.split(".", 1)[1] for e in entities if "." in e}
    for match in _NAMED_FLAG.findall(core):
        upper = match.upper()
        if upper not in seen and upper not in dotted_bits:
            seen.add(upper)
            entities.append(upper)

    return tuple(entities)


def _entity_tokens(entity: str) -> tuple[str, ...]:
    """Search tokens for matching entity in chunk text."""
    tokens = [entity]
    if "." in entity:
        reg, bit = entity.split(".", 1)
        tokens.extend([reg, bit, f"{reg}.{bit}"])
    if entity.startswith("#"):
        tokens.append(entity[1:])
    return tuple(dict.fromkeys(t.upper() for t in tokens))


def _entity_in_text(text: str, entity: str) -> bool:
    upper = text.upper()
    if entity.upper() in upper:
        return True
    if "." in entity:
        bit = entity.split(".", 1)[1].upper()
        if re.search(rf"\b{re.escape(bit)}\b", upper):
            return True
    return False


def _is_usage_heavy(text: str) -> bool:
    return any(p.search(text) for p in _USAGE_SIGNALS)


def authoritative_definition_score(text: str, entity: str) -> int:
    """
    Score 0–15 for how authoritative a chunk is as an entity definition.

    Scores >= 8 are treated as pin-worthy authoritative definitions.
    """
    if not _entity_in_text(text, entity):
        return 0

    score = 0

    for pattern in _ENTITY_PATTERNS.get(entity.upper(), ()):
        if pattern.search(text):
            score += 10

    if _EM_DASH_DEF.search(text) and _entity_in_text(text, entity):
        score += 4
    if _BIT_OF_REGISTER.search(text):
        score += 8
    if _BRACKET_BIT.search(text):
        score += 7
    if _BIT_NUMBER.search(text):
        score += 5
    if _FLAG_WORD.search(text):
        score += 3
    if _FIGURE.search(text):
        score += 3
    if _CONTAINS.search(text):
        score += 2

    # Entity-specific bit/name on same line
    short = entity.split(".")[-1]
    if re.search(rf"{re.escape(short)}\s*[—–-]", text, re.I):
        score += 6

    if _is_usage_heavy(text) and score < 10:
        score -= 4

    return max(score, 0)


def is_authoritative_definition(text: str, entity: str) -> bool:
    return authoritative_definition_score(text, entity) >= _AUTHORITATIVE_THRESHOLD


def classify_chunk_tier(text: str, entities: tuple[str, ...]) -> int:
    """
    0 = authoritative definition, 1 = definitional, 2 = behavior, 3 = procedural/other.
    """
    if entities and any(is_authoritative_definition(text, e) for e in entities):
        return 0
    if entities and any(authoritative_definition_score(text, e) >= 4 for e in entities):
        return 1
    if re.search(r"\b(when set|when clear|enables|disables|causes)\b", text, re.I):
        return 2
    return 3


def requires_exact_definition(query: str) -> bool:
    """Whether the query demands authoritative register/flag definitions."""
    core = extract_core_query(query)
    entities = extract_register_entities(query)
    if not entities:
        return False

    exact_triggers = (
        r"\bdifferentiate\b",
        r"\bcompare\b",
        r"\bcontrast\b",
        r"\bbit\s+(?:number|position)\b",
        r"\bexact\s+(?:meaning|definition)\b",
        r"\bwhat\s+is\b",
        r"\bdefine\b",
        r"\bexplain\b",
        r"\bmeaning\s+of\b",
        r"\bwhich\s+bit\b",
    )
    if any(re.search(p, core, re.I) for p in exact_triggers):
        return True
    return bool(_DOTTED_ENTITY.search(core))


def resolve_authoritative_definitions(
    all_chunks: list[RetrievedChunk],
    query: str,
    *,
    max_per_entity: int = 1,
    max_total: int = 3,
) -> list[DefinitionMatch]:
    """
    Scan corpus for authoritative definition chunks per query entity.

    Returns best matching chunk per entity, deduplicated by chunk_id.
    """
    entities = extract_register_entities(query)
    if not entities:
        return []

    matches: list[DefinitionMatch] = []
    used_chunk_ids: set[str] = set()

    for entity in entities:
        entity_matches: list[DefinitionMatch] = []
        for chunk in all_chunks:
            score = authoritative_definition_score(chunk.text, entity)
            if score < _AUTHORITATIVE_THRESHOLD:
                continue
            entity_matches.append(
                DefinitionMatch(
                    entity=entity,
                    chunk=chunk,
                    score=score,
                    authoritative=True,
                )
            )

        entity_matches.sort(key=lambda m: m.score, reverse=True)
        added = 0
        for match in entity_matches:
            if match.chunk.chunk_id in used_chunk_ids:
                continue
            matches.append(match)
            used_chunk_ids.add(match.chunk.chunk_id)
            added += 1
            if added >= max_per_entity:
                break

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:max_total]


def pin_definition_chunks(
    matches: list[DefinitionMatch],
) -> list[RetrievedChunk]:
    """Convert definition matches to pinned retrieval chunks."""
    pinned: list[RetrievedChunk] = []
    for match in matches:
        meta = dict(match.chunk.metadata)
        meta["pinned_definition"] = True
        meta["definition_entity"] = match.entity
        meta["authoritative_score"] = match.score
        meta["retrieval_method"] = meta.get("retrieval_method", "definition_resolver")
        meta["chunk_tier"] = 0
        meta["rerank_score"] = max(float(meta.get("rerank_score", 1.0)), 1.0)
        pinned.append(
            RetrievedChunk(
                chunk_id=match.chunk.chunk_id,
                text=match.chunk.text,
                page_number=match.chunk.page_number,
                chunk_index=match.chunk.chunk_index,
                score=999.0 + match.score,
                metadata=meta,
            )
        )
    return pinned


def merge_pinned_with_reranked(
    pinned: list[RetrievedChunk],
    reranked: list[RetrievedChunk],
    top_k: int,
) -> list[RetrievedChunk]:
    """Force pinned definition chunks into final context; never drop them."""
    if not pinned:
        return reranked[:top_k]

    pinned_ids = {c.chunk_id for c in pinned}
    tail = [c for c in reranked if c.chunk_id not in pinned_ids]
    slots = max(top_k - len(pinned), 0)
    return pinned + tail[:slots]


def sort_definition_first(
    chunks: list[RetrievedChunk],
    entities: tuple[str, ...],
) -> list[RetrievedChunk]:
    """Order context: authoritative definition → definitional → behavior → procedural."""
    def sort_key(chunk: RetrievedChunk) -> tuple:
        tier = chunk.metadata.get("chunk_tier")
        if tier is None:
            tier = classify_chunk_tier(chunk.text, entities)
        pinned = 0 if chunk.metadata.get("pinned_definition") else 1
        rerank = -float(chunk.metadata.get("rerank_score", chunk.score))
        return (pinned, tier, rerank)

    return sorted(chunks, key=sort_key)


def authoritative_coverage(
    chunks: list[RetrievedChunk],
    query: str,
) -> tuple[bool, list[str]]:
    """
    Check whether every query entity has an authoritative definition in chunks.

    Returns (all_covered, missing_entities).
    """
    entities = extract_register_entities(query)
    if not entities:
        return True, []

    covered: set[str] = set()
    for entity in entities:
        for chunk in chunks:
            if is_authoritative_definition(chunk.text, entity):
                covered.add(entity)
                break

    missing = [e for e in entities if e not in covered]
    return len(missing) == 0, missing
