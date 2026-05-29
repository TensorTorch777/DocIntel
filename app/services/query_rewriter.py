"""Lightweight query rewriting for technical retrieval."""

import logging
import re

from app.services.entity_matcher import extract_entities
from app.services.query_preprocess import extract_core_query

logger = logging.getLogger(__name__)

_QUERY_REWRITE_LLM_PROMPT = """You expand a technical documentation search query.
Rules:
- Output ONE line only — no explanation
- Keep all original terms from the user query
- Add closely related register names, bit names, exception names, and synonyms
- Do NOT answer the question
- Do NOT remove specificity

User query: {query}
Expanded search query:"""


def rule_based_expand(core_query: str) -> str:
    """Expand core query using entity extraction and synonym map."""
    entities = extract_entities(core_query)
    parts = [core_query.strip()]

    if entities.registers:
        parts.extend(entities.registers)
    if entities.exceptions:
        parts.extend(entities.exceptions)
    if entities.flags:
        parts.extend(entities.flags)
    if entities.expansion_terms:
        parts.extend(entities.expansion_terms)

    seen: set[str] = set()
    tokens: list[str] = []
    for part in parts:
        for token in part.split():
            key = token.lower()
            if key not in seen:
                seen.add(key)
                tokens.append(token)

    expanded = " ".join(tokens)
    logger.debug("Rule-based query expand: %r -> %r", core_query, expanded)
    return expanded


async def expand_query(
    query: str,
    llm_service=None,
    use_llm: bool = False,
) -> tuple[str, str, str]:
    """
    Return (original_query, core_query, retrieval_query).

    Prompt-control sections are stripped before expansion.
    """
    original_query = query.strip()
    core_query = extract_core_query(original_query)
    retrieval_query = rule_based_expand(core_query)

    if use_llm and llm_service is not None:
        try:
            llm_line = await llm_service.complete(
                "You expand search queries for technical manuals.",
                _QUERY_REWRITE_LLM_PROMPT.format(query=core_query),
                temperature=0.0,
            )
            llm_line = llm_line.strip().split("\n")[0].strip()
            if llm_line and len(llm_line) > len(core_query) // 2:
                retrieval_query = rule_based_expand(f"{core_query} {llm_line}")
        except Exception:
            logger.warning("LLM query rewrite failed; using rule-based only")

    return original_query, core_query, retrieval_query
