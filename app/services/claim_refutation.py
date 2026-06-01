"""Detect when retrieved evidence refutes a user's entity-attribution claim."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.query_preprocess import extract_core_query
from app.services.register_definition_resolver import (
    authoritative_definition_score,
    extract_register_entities,
    is_authoritative_definition,
)
from app.services.vector_store import RetrievedChunk

_REGISTER = re.compile(r"\b(CR[0-8])\b", re.I)

# Query asks whether entity E has role R
_ROLE_CLAIM = re.compile(
    r"\b(?:does|do|is|are|can)\s+(?:the\s+)?("
    r"CR[0-8]|IA32_[A-Z0-9_]+"
    r")\b.{0,120}?"
    r"(?:store|hold|contain|keep|save|record|load|capture|receive)",
    re.I | re.S,
)

_IS_ROLE_QUERY = re.compile(
    r"\b(?:is|are)\s+(?:the\s+)?("
    r"CR[0-8]|IA32_[A-Z0-9_]+"
    r")\b.{0,80}?"
    r"(?:the\s+)?(.{3,60}?)\??\s*$",
    re.I | re.S,
)

# Evidence assigns role to a register
_LOADS_REGISTER_WITH = re.compile(
    r"(?:loads?|stores?|holds?|contains?|writes?|saves?)\s+(?:the\s+)?"
    r"(CR[0-8])\s+register\s+with\s+(.{5,80}?)(?:\.|$|;|\n)",
    re.I,
)
_REGISTER_ROLE_DEF = re.compile(
    r"(CR[0-8])\s*[—–-]\s*(.{5,80})",
    re.I,
)

_ROLE_KEYWORDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"faulting address|linear address|address that generated", re.I), "faulting linear address"),
    (re.compile(r"page-directory base|page directory base|PDBR", re.I), "page-directory base"),
    (re.compile(r"page.global enable|PGE", re.I), "page global enable"),
    (re.compile(r"paging enable|\bPG\b", re.I), "paging enable"),
)


@dataclass(frozen=True)
class ClaimRefutation:
    """Evidence that disproves the queried entity attribution."""

    queried_entity: str
    alternative_entity: str
    role: str
    evidence_text: str
    chunk: RetrievedChunk
    source_index: int = 1
    authoritative: bool = False

    def format_answer(self) -> str:
        page = self.chunk.page_number
        src = self.source_index
        return (
            f"NO. {self.evidence_text.strip()} "
            f"[Source {src}, p. {page}]"
        )


def _normalize_entity(entity: str) -> str:
    return entity.upper().split(".")[0]


def _role_from_query(query: str) -> str | None:
    core = extract_core_query(query)
    for pattern, role in _ROLE_KEYWORDS:
        if pattern.search(core):
            return role
    return None


def _queried_entity(query: str) -> str | None:
    entities = extract_register_entities(query)
    if entities:
        return _normalize_entity(entities[0])
    match = _ROLE_CLAIM.search(query) or _IS_ROLE_QUERY.search(query)
    if match:
        return _normalize_entity(match.group(1))
    return None


def _entities_in_text(text: str) -> set[str]:
    return {_normalize_entity(m) for m in _REGISTER.findall(text)}


def _text_supports_role(text: str, role: str | None) -> bool:
    if not role:
        return True
    role_lower = role.lower()
    text_lower = text.lower()
    if role_lower in text_lower:
        return True
    for pattern, label in _ROLE_KEYWORDS:
        if label == role and pattern.search(text):
            return True
    return False


def _find_register_role_conflict(
    chunks: list[RetrievedChunk],
    queried: str,
    role: str,
) -> ClaimRefutation | None:
    """Is CR2 the page-directory base? → evidence naming CR3 as PDBR."""
    role_terms = [
        p for p, label in _ROLE_KEYWORDS if label == role
    ]
    for idx, chunk in enumerate(chunks, start=1):
        text = chunk.text
        if not any(p.search(text) for p in role_terms):
            continue
        for match in _REGISTER_ROLE_DEF.finditer(text):
            entity = _normalize_entity(match.group(1))
            if entity != queried and _text_supports_role(match.group(2), role):
                if is_authoritative_definition(text, entity) or authoritative_definition_score(text, entity) >= 4:
                    return ClaimRefutation(
                        queried_entity=queried,
                        alternative_entity=entity,
                        role=role,
                        evidence_text=(
                            f"Sources assign {role} to {entity}, not {queried}: "
                            f"{match.group(0).strip()}"
                        ),
                        chunk=chunk,
                        source_index=idx,
                        authoritative=True,
                    )
    return None


def _find_entity_substitution(
    chunks: list[RetrievedChunk],
    queried: str,
    role: str | None,
) -> ClaimRefutation | None:
    for idx, chunk in enumerate(chunks, start=1):
        text = chunk.text
        if not _text_supports_role(text, role):
            continue

        match = _LOADS_REGISTER_WITH.search(text)
        if match:
            entity = _normalize_entity(match.group(1))
            detail = match.group(2).strip()
            if entity != queried:
                return ClaimRefutation(
                    queried_entity=queried,
                    alternative_entity=entity,
                    role=role or "the stated role",
                    evidence_text=(
                        f"The processor loads {entity} (not {queried}) with {detail.rstrip('.')}"
                    ),
                    chunk=chunk,
                    source_index=idx,
                )

        # "The contents of the CR2 register" + loads CR2 with linear address
        if re.search(rf"\b{re.escape(queried)}\b", text, re.I):
            continue
        for entity in _entities_in_text(text):
            if entity == queried:
                continue
            if re.search(
                rf"(?:contents of the )?{re.escape(entity)}\s+register",
                text,
                re.I,
            ) and re.search(r"linear address|faulting address|address that generated", text, re.I):
                sentence = _best_sentence(text, entity)
                return ClaimRefutation(
                    queried_entity=queried,
                    alternative_entity=entity,
                    role=role or "faulting linear address",
                    evidence_text=sentence,
                    chunk=chunk,
                    source_index=idx,
                )
    return None


def _best_sentence(text: str, entity: str) -> str:
    for part in re.split(r"(?<=[.!?])\s+", text):
        if entity in part.upper() and re.search(
            r"linear address|faulting address|loads?|stores?", part, re.I
        ):
            return part.strip()
    return text.strip()[:240]


def detect_claim_refutation(
    chunks: list[RetrievedChunk],
    query: str,
) -> ClaimRefutation | None:
    """
    Return refutation when sources assign the queried role to a different entity.

    Example: "Does CR3 store the faulting address?" + CR2 loads linear address → refuted.
    """
    queried = _queried_entity(query)
    if not queried:
        return None

    role = _role_from_query(query)

    sub = _find_entity_substitution(chunks, queried, role)
    if sub:
        return sub

    if role:
        conflict = _find_register_role_conflict(chunks, queried, role)
        if conflict:
            return conflict

    # Definition claim validation: CR0.PG means Page Global Enable
    if re.search(r"\bmeans\b", query, re.I):
        return _find_definition_mismatch(chunks, query)

    return None


def _find_definition_mismatch(
    chunks: list[RetrievedChunk],
    query: str,
) -> ClaimRefutation | None:
    entities = extract_register_entities(query)
    if not entities:
        return None

    claimed = query
    pg_global = re.search(r"page\s+global\s+enable", query, re.I)
    paging = re.search(r"paging\s+enable|\bpaging\b", query, re.I)

    for entity in entities:
        for idx, chunk in enumerate(chunks, start=1):
            text = chunk.text
            if not is_authoritative_definition(text, entity) and authoritative_definition_score(text, entity) < 4:
                continue
            if pg_global and entity.upper() == "CR0.PG":
                if re.search(r"paging\s*\(|PG\s*[—–-]\s*Paging", text, re.I):
                    return ClaimRefutation(
                        queried_entity=entity,
                        alternative_entity="CR4.PGE",
                        role="page global enable",
                        evidence_text=(
                            f"CR0.PG is Paging Enable, not Page Global Enable "
                            f"(Page Global Enable is CR4.PGE)"
                        ),
                        chunk=chunk,
                        source_index=idx,
                        authoritative=True,
                    )
            if paging and entity.upper() == "CR4.PGE":
                if re.search(r"page\s+global\s+enable", text, re.I):
                    return ClaimRefutation(
                        queried_entity=entity,
                        alternative_entity="CR0.PG",
                        role="paging enable",
                        evidence_text=(
                            f"CR4.PGE is Page Global Enable, not Paging Enable "
                            f"(Paging Enable is CR0.PG)"
                        ),
                        chunk=chunk,
                        source_index=idx,
                        authoritative=True,
                    )
    return None
