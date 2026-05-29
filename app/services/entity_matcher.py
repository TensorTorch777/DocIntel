"""Technical entity extraction and retrieval boosting."""

import re
from dataclasses import dataclass

# Whitelist: control/debug registers and IA32 MSRs only (no generic Rxx matches)
_REGISTER_PATTERN = re.compile(
    r"\b(CR[0-8]|DR[0-7]|TR[0-7]|IA32_[A-Z0-9_]+)\b",
    re.I,
)
# General-purpose / segment registers (explicit names only)
_GPR_PATTERN = re.compile(
    r"\b(EAX|EBX|ECX|EDX|ESI|EDI|ESP|EBP|EIP|EFLAGS|"
    r"RAX|RBX|RCX|RDX|RSI|RDI|RSP|RBP|RIP|R8|R9|R10|R11|R12|R13|R14|R15)\b",
    re.I,
)
_EXCEPTION_PATTERN = re.compile(r"#(?:PF|GP|DF|NP|TS|SS|AC|MC|XM|VE|CP)\b", re.I)
_FLAG_PATTERN = re.compile(r"\b(PG|PE|PAE|LME|WP|CD|NW|AM|TS|ET|EM|MP|NXE|PGE|SMEP|SMAP)\b")

_ENTITY_BLACKLIST = frozenset(
    {
        "RULES",
        "RULE",
        "EVIDENCE",
        "REGISTER",
        "EXTERNAL",
        "OUTPUT",
        "JSON",
        "FORMAT",
        "ONLY",
        "REQUIREMENTS",
        "REQUIREMENT",
        "INSTRUCTIONS",
        "INSTRUCTION",
        "MENTION",
        "QUOTE",
        "ANSWER",
        "KNOWLEDGE",
        "SOURCE",
        "PAGE",
        "YES",
        "NO",
        "FIRST",
        "STRICT",
        "RESPONSE",
        "CONSTRAINTS",
        "NOTES",
    }
)

# Lightweight synonym expansion for retrieval queries (not for generation)
_ENTITY_EXPANSIONS: dict[str, str] = {
    "page fault": "page fault exception #PF CR2 linear address faulting address",
    "cr3": "CR3 control register page-directory base PML4",
    "cr2": "CR2 page-fault linear address linear address",
    "cr0": "CR0 control register PG PE paging",
    "cr4": "CR4 control register PAE PSE",
    "ia32_efer": "IA32_EFER LME NXE long mode enable execute disable extended feature",
    "ia-32e": "IA-32e long mode 64-bit mode paging segmentation",
    "canonical": "canonical address canonical form sign-extension 64-bit",
    "canonical addressing": "canonical address linear address sign-extension bits",
    "paging": "paging page tables PML4 PDPT PD PT CR3",
    "segmentation": "segmentation segment descriptor GDT LDT",
}


@dataclass(frozen=True)
class TechnicalEntities:
    """Entities extracted from a user query."""

    registers: tuple[str, ...]
    exceptions: tuple[str, ...]
    flags: tuple[str, ...]
    expansion_terms: tuple[str, ...]


def _filter_blacklisted(tokens: list[str]) -> tuple[str, ...]:
    """Drop prompt-control tokens mistaken for technical entities."""
    seen: set[str] = set()
    out: list[str] = []
    for token in tokens:
        upper = token.upper()
        if upper in _ENTITY_BLACKLIST:
            continue
        if upper not in seen:
            seen.add(upper)
            out.append(upper)
    return tuple(out)


def extract_entities(query: str) -> TechnicalEntities:
    """Extract x86/Intel technical tokens from a query."""
    registers = _filter_blacklisted(
        list(_REGISTER_PATTERN.findall(query)) + list(_GPR_PATTERN.findall(query))
    )
    exceptions = _filter_blacklisted(list(_EXCEPTION_PATTERN.findall(query)))
    flags = _filter_blacklisted(list(_FLAG_PATTERN.findall(query)))

    lower = query.lower()
    expansions: list[str] = []
    for key, terms in _ENTITY_EXPANSIONS.items():
        if key in lower:
            expansions.extend(terms.split())

    if "page fault" in lower and "CR2" not in registers and "CR3" in registers:
        expansions.extend(["CR2", "page-fault", "linear", "address"])

    unique_expansions = _filter_blacklisted(expansions)
    return TechnicalEntities(
        registers=registers,
        exceptions=exceptions,
        flags=flags,
        expansion_terms=unique_expansions,
    )


def entity_match_count(text: str, entities: TechnicalEntities) -> int:
    """Count exact token hits in chunk text."""
    upper = text.upper()
    count = 0
    for reg in entities.registers:
        if reg in upper:
            count += 2
    for exc in entities.exceptions:
        if exc in upper:
            count += 2
    for flag in entities.flags:
        if re.search(rf"\b{re.escape(flag)}\b", upper):
            count += 1
    for term in entities.expansion_terms:
        if term.upper() in upper or term.lower() in text.lower():
            count += 1
    return count


def apply_entity_boost(
    chunks: list,
    entities: TechnicalEntities,
    boost_per_hit: float = 0.08,
) -> list:
    """Boost RRF/rerank scores for chunks containing query entities."""
    if not entities.registers and not entities.exceptions and not entities.expansion_terms:
        return chunks

    boosted = []
    for chunk in chunks:
        hits = entity_match_count(chunk.text, entities)
        meta = dict(chunk.metadata)
        meta["entity_hits"] = hits
        if hits:
            meta["entity_boost"] = hits * boost_per_hit
            new_score = chunk.score + hits * boost_per_hit
        else:
            meta["entity_boost"] = 0.0
            new_score = chunk.score

        boosted.append(
            type(chunk)(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                score=new_score,
                metadata=meta,
            )
        )

    boosted.sort(key=lambda c: c.score, reverse=True)
    return boosted
