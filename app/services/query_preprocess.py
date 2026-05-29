"""Strip prompt-control language before retrieval and entity extraction."""

import re

# Section headers that start meta-instructions, not semantic content
_SECTION_HEADER = re.compile(
    r"(?im)^\s*(?:"
    r"rules?(?:\s*(?:for\s*)?(?:the\s*)?(?:answer|response))?"
    r"|requirements?"
    r"|instructions?"
    r"|answer\s*format"
    r"|output\s*format"
    r"|response\s*format"
    r"|format(?:\s*constraints?)?"
    r"|(?:strict\s*)?json(?:\s*output)?"
    r"|output\s*only"
    r"|constraints?"
    r"|notes?"
    r")\s*:?\s*$"
)

# Inline meta phrases sometimes appended to the question
_META_PHRASES = (
    r"no\s+external\s+knowledge",
    r"quote\s+evidence",
    r"mention\s+(?:the\s+)?source",
    r"mention\s+(?:the\s+)?page",
    r"yes\s+or\s+no\s+first",
    r"output\s+only",
    r"strict\s+json",
    r"answer\s+format",
    r"do\s+not\s+use\s+prior\s+knowledge",
)


def extract_core_query(query: str) -> str:
    """
    Return semantic question content only.

    Strips trailing Rules/Requirements/Format sections and common
    prompt-control phrases so retrieval sees technical content only.
    """
    text = query.strip()
    if not text:
        return query

    section = _SECTION_HEADER.search(text)
    if section:
        text = text[: section.start()].strip()

    for pattern in _META_PHRASES:
        text = re.sub(pattern, " ", text, flags=re.I)

    text = re.sub(r"\s+", " ", text).strip(" \t\n\r-•*")
    return text or query.strip()
