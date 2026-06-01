"""Procedural query detection, step extraction, ordering, and answer formatting."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.query_preprocess import extract_core_query
from app.services.vector_store import RetrievedChunk

def is_procedural_query(query: str) -> bool:
    """Detect queries requesting ordered procedures or sequences."""
    from app.services.query_intent import is_procedural_intent

    return is_procedural_intent(query)


_NUMBERED_LINE = re.compile(r"^\s*(\d+)[\.)]\s+(.+)$", re.MULTILINE)
_BULLET_LINE = re.compile(r"^\s*[-•*]\s+(.+)$", re.MULTILINE)
_STEP_HEADER = re.compile(r"^\s*Step\s+(\d+)\s*[:\.]?\s*(.+)$", re.MULTILINE | re.I)

_TEMPORAL_PHRASES: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"\bfirst\b", re.I), 0),
    (re.compile(r"\bmust first\b", re.I), 0),
    (re.compile(r"\bbefore\b", re.I), 1),
    (re.compile(r"\bthen\b", re.I), 2),
    (re.compile(r"\bnext\b", re.I), 2),
    (re.compile(r"\bafter\b", re.I), 3),
    (re.compile(r"\bfinally\b", re.I), 4),
    (re.compile(r"\blast\b", re.I), 4),
)

_DEPENDENCY_BEFORE = re.compile(r"\bbefore\s+(.+?)(?:[.;]|$)", re.I)
_DEPENDENCY_AFTER = re.compile(r"\bafter\s+(.+?)(?:[.;]|$)", re.I)
_DEPENDENCY_MUST_FIRST = re.compile(r"\bmust first\b", re.I)


@dataclass
class ExtractedStep:
    """A single procedural step extracted from evidence."""

    text: str
    source_index: int
    explicit_number: int | None = None
    temporal_rank: int = 2
    dependencies: list[str] = field(default_factory=list)
    line_key: str = ""
    relevance_score: float = 0.0

    def normalized_text(self) -> str:
        return re.sub(r"\s+", " ", self.text.strip().lower())


_QUERY_STOPWORDS = frozenset(
    {
        "what", "how", "does", "the", "and", "for", "with", "from", "that", "this",
        "are", "is", "of", "in", "to", "a", "an", "on", "or", "be", "by", "at",
        "explain", "describe", "define", "list", "which", "when", "where", "why",
        "step", "steps", "sequence", "process", "procedure", "ordered", "happens",
    }
)

_ACTION_VERBS = re.compile(
    r"\b(set|enable|disable|load|switch|configure|initialize|initialise|enter|"
    r"flush|transition|establish|clear|turn\s+on|turn\s+off)\b",
    re.I,
)

_DOTTED_ENTITY = re.compile(
    r"\b(CR[0-8]\.[A-Z0-9]+|IA32_[A-Z0-9_]+(?:\.[A-Z0-9]+)?)\b",
    re.I,
)
_REGISTER = re.compile(r"\b(CR[0-8]|IA32_EFER|GDTR|IDTR|LGDT|LIDT)\b", re.I)
_NAMED_FLAG = re.compile(r"\b(NXE|PGE|PG|PE|PAE|LME|WP|SMEP|SMAP)\b", re.I)

_ACTION_SYNONYMS: dict[str, tuple[str, ...]] = {
    "switch": ("switch", "enter", "transition", "load", "set", "enable", "perform"),
    "enable": ("enable", "set", "activate", "turn on", "establish"),
    "disable": ("disable", "clear", "turn off"),
    "load": ("load", "lgdt", "lidt", "establish"),
    "configure": ("configure", "initialize", "initialise", "setup", "set up"),
    "enter": ("enter", "switch", "transition"),
    "initialize": ("initialize", "initialise", "setup", "configure", "load"),
    "flush": ("flush", "invalidate", "clear"),
    "transition": ("transition", "switch", "enter"),
    "establish": ("establish", "load", "configure", "set"),
    "clear": ("clear", "disable", "flush"),
}

# Query-intent profiles: boost on-topic steps, penalize off-topic noise
_INTENT_PROFILES: list[dict] = [
    {
        "triggers": [r"protected mode", r"enter protected", r"switch to protected"],
        "boost": ["CR0.PE", "PE", "LGDT", "LIDT", "GDT", "IDT", "far jump", "segment"],
        "penalize": ["paging", "CR0.PG", " PG ", "TSS", "VMX", "long mode", "EFER.LME"],
    },
    {
        "triggers": [r"enable paging", r"paging on", r"turn on paging", r"activate paging"],
        "boost": ["CR0.PG", "CR3", "page table", "PML4", "paging", "PG"],
        "penalize": ["TSS", "VMX", "SMEP", "SMAP", "long mode"],
    },
    {
        "triggers": [r"long mode", r"ia-32e", r"64-bit mode", r"enter ia-32e", r"enter long mode"],
        "boost": ["PAE", "EFER.LME", "LME", "CR0.PG", "paging", "far jump", "EFER"],
        "penalize": ["real mode", "VMX", "SMM", "SGX"],
    },
    {
        "triggers": [r"execute.disable", r"\bNX\b", r"enable nx", r"no-execute"],
        "boost": ["NXE", "EFER", "PTE", "No-Execute"],
        "penalize": ["VMX", "TSS", "real mode"],
    },
    {
        "triggers": [r"page fault", r"#PF", r"on a page fault"],
        "boost": ["CR2", "page fault", "linear address", "error code"],
        "penalize": ["LGDT", "VMX", "SMEP"],
    },
    {
        "triggers": [r"switch cr3", r"change cr3", r"tlb flush", r"flush tlb"],
        "boost": ["CR3", "TLB", "invalidate", "flush"],
        "penalize": ["LGDT", "far jump", "VMX"],
    },
    {
        "triggers": [r"smep", r"supervisor mode execution"],
        "boost": ["SMEP", "CR4"],
        "penalize": ["paging", "LGDT", "TSS"],
    },
    {
        "triggers": [r"configure idt", r"load idt", r"interrupt descriptor", r"\bidt\b"],
        "boost": ["IDTR", "LIDT", "IDT", "interrupt descriptor", "gate descriptor"],
        "penalize": ["paging", "CR0.PG", "VMX", "GDT"],
    },
    {
        "triggers": [r"load gdt", r"configure gdt", r"global descriptor"],
        "boost": ["GDTR", "LGDT", "GDT", "global descriptor"],
        "penalize": ["paging", "CR0.PG", "TSS", "VMX"],
    },
]


def _temporal_rank(text: str) -> int:
    ranks = [score for pattern, score in _TEMPORAL_PHRASES if pattern.search(text)]
    return min(ranks) if ranks else 2


def _extract_dependencies(text: str) -> list[str]:
    deps: list[str] = []
    if _DEPENDENCY_MUST_FIRST.search(text):
        deps.append("__FIRST__")
    before = _DEPENDENCY_BEFORE.search(text)
    if before:
        deps.append(before.group(1).strip().lower()[:80])
    after = _DEPENDENCY_AFTER.search(text)
    if after:
        deps.append(f"after:{after.group(1).strip().lower()[:80]}")
    return deps


def _clean_step_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"^\d+[\.)]\s*", "", text)
    text = re.sub(r"^[-•*]\s*", "", text)
    return text.strip()


def extract_steps_from_text(text: str, source_index: int) -> list[ExtractedStep]:
    """Extract numbered, bulleted, and temporal steps from chunk text."""
    steps: list[ExtractedStep] = []
    seen_lines: set[str] = set()

    def add_step(raw: str, explicit_number: int | None = None) -> None:
        cleaned = _clean_step_text(raw)
        if len(cleaned) < 12:
            return
        key = cleaned.lower()[:120]
        if key in seen_lines:
            return
        seen_lines.add(key)
        steps.append(
            ExtractedStep(
                text=cleaned,
                source_index=source_index,
                explicit_number=explicit_number,
                temporal_rank=_temporal_rank(cleaned),
                dependencies=_extract_dependencies(cleaned),
                line_key=key,
            )
        )

    for match in _NUMBERED_LINE.finditer(text):
        add_step(match.group(2), explicit_number=int(match.group(1)))

    for match in _BULLET_LINE.finditer(text):
        add_step(match.group(1))

    for match in _STEP_HEADER.finditer(text):
        add_step(match.group(2), explicit_number=int(match.group(1)))

    # Sentences with strong temporal / imperative procedural language
    for sentence in re.split(r"(?<=[.;])\s+", text):
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue
        if any(p.search(sentence) for p, _ in _TEMPORAL_PHRASES):
            add_step(sentence)
        elif re.search(r"\b(set|clear|enable|disable|load|switch|configure|initialize)\b", sentence, re.I):
            if re.search(r"\b(CR[0-8]|EFER|MSR|PAE|PG|paging|GDT|IDT)\b", sentence, re.I):
                add_step(sentence)

    return steps


def extract_steps_from_chunks(chunks: list[RetrievedChunk]) -> list[ExtractedStep]:
    """Extract steps from all retrieved chunks with 1-based source indices."""
    all_steps: list[ExtractedStep] = []
    global_seen: set[str] = set()

    for i, chunk in enumerate(chunks, start=1):
        for step in extract_steps_from_text(chunk.text, source_index=i):
            if step.line_key in global_seen:
                continue
            global_seen.add(step.line_key)
            all_steps.append(step)

    return all_steps


def _significant_terms(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]{3,}", text.lower())
    return {t for t in tokens if t not in _QUERY_STOPWORDS}


def _intent_expanded_terms(query: str) -> set[str]:
    """Add boost-token terms when a query matches an intent profile."""
    terms: set[str] = set()
    lower_q = query.lower()
    for profile in _INTENT_PROFILES:
        if not any(re.search(t, lower_q) for t in profile["triggers"]):
            continue
        for token in profile["boost"]:
            terms.update(re.findall(r"[a-z0-9]{3,}", token.lower()))
    return terms


def _expanded_action_terms(actions: tuple[str, ...]) -> set[str]:
    expanded: set[str] = set(actions)
    for action in actions:
        expanded.update(_ACTION_SYNONYMS.get(action, (action,)))
    return expanded


def _query_entities(query: str) -> tuple[str, ...]:
    core = extract_core_query(query)
    seen: set[str] = set()
    entities: list[str] = []
    for match in _DOTTED_ENTITY.findall(core):
        upper = match.upper()
        if upper not in seen:
            seen.add(upper)
            entities.append(upper)
    for match in _REGISTER.findall(core):
        upper = match.upper()
        if upper not in seen:
            seen.add(upper)
            entities.append(upper)
    for match in _NAMED_FLAG.findall(core):
        upper = match.upper()
        if upper not in seen:
            seen.add(upper)
            entities.append(upper)
    lower_q = query.lower()
    for profile in _INTENT_PROFILES:
        if not any(re.search(t, lower_q) for t in profile["triggers"]):
            continue
        for token in profile["boost"]:
            upper = token.upper()
            if upper not in seen:
                seen.add(upper)
                entities.append(upper)
    return tuple(entities)


def _query_actions(query: str) -> tuple[str, ...]:
    core = extract_core_query(query)
    return tuple(dict.fromkeys(m.group(1).lower() for m in _ACTION_VERBS.finditer(core)))


def _entity_in_step(step_text: str, entity: str) -> bool:
    upper = step_text.upper()
    ent = entity.upper()
    if ent in upper:
        return True
    if " " in ent:
        return all(part in upper for part in ent.split())
    if "." in ent:
        bit = ent.split(".", 1)[1]
        return bit in upper
    return False


def query_similarity(step_text: str, query: str) -> float:
    q_terms = _significant_terms(query) | _intent_expanded_terms(query)
    if not q_terms:
        return 0.5
    s_terms = _significant_terms(step_text)
    overlap = len(q_terms & s_terms)
    return min(1.0, overlap / len(q_terms))


def entity_overlap_score(step_text: str, entities: tuple[str, ...]) -> float:
    if not entities:
        return 0.65
    hits = sum(1 for e in entities if _entity_in_step(step_text, e))
    if hits == 0:
        return 0.15
    return min(1.0, hits / 2.0)


def action_overlap_score(step_text: str, actions: tuple[str, ...]) -> float:
    if not actions:
        return 0.65
    step_l = step_text.lower()
    expanded = _expanded_action_terms(actions)
    hits = sum(1 for a in expanded if a in step_l)
    return min(1.0, hits / len(actions))


def intent_multiplier(step_text: str, query: str) -> float:
    """Apply query-intent boost/penalty profiles."""
    mult = 1.0
    lower_q = query.lower()
    lower_s = step_text.lower()
    for profile in _INTENT_PROFILES:
        if not any(re.search(t, lower_q) for t in profile["triggers"]):
            continue
        for token in profile["boost"]:
            if token.lower() in lower_s:
                mult *= 1.4
        for token in profile["penalize"]:
            if token.lower() in lower_s:
                mult *= 0.55
    return mult


def score_step_relevance(step: ExtractedStep, query: str) -> float:
    """
    Relevance = query_similarity × entity_overlap × action_overlap × intent_multiplier.
    """
    entities = _query_entities(query)
    actions = _query_actions(query)
    q_sim = query_similarity(step.text, query)
    ent = max(entity_overlap_score(step.text, entities), 0.15)
    act = max(action_overlap_score(step.text, actions), 0.15)
    score = q_sim * ent * act * intent_multiplier(step.text, query)
    return min(1.0, score)


def filter_steps_by_relevance(
    steps: list[ExtractedStep],
    query: str,
    *,
    max_steps: int = 10,
    min_score: float = 0.08,
    min_keep: int = 1,
) -> list[ExtractedStep]:
    """Keep top-N steps most relevant to the user question."""
    if not steps:
        return []
    if len(steps) <= max_steps:
        return [
            ExtractedStep(
                text=s.text,
                source_index=s.source_index,
                explicit_number=s.explicit_number,
                temporal_rank=s.temporal_rank,
                dependencies=list(s.dependencies),
                line_key=s.line_key,
                relevance_score=score_step_relevance(s, query),
            )
            for s in steps
        ]

    # Light pass: drop heavily penalized off-topic steps before top-N when moderately over cap
    if len(steps) <= max_steps + 6:
        scored_light = [(s, score_step_relevance(s, query)) for s in steps]
        kept = [
            s for s, sc in scored_light if intent_multiplier(s.text, query) >= 0.6 and sc >= min_score * 0.5
        ]
        if len(kept) >= min_keep:
            kept_keys = {s.line_key for s in kept[:max_steps]}
            score_map = {s.line_key: sc for s, sc in scored_light}
            return [
                ExtractedStep(
                    text=s.text,
                    source_index=s.source_index,
                    explicit_number=s.explicit_number,
                    temporal_rank=s.temporal_rank,
                    dependencies=list(s.dependencies),
                    line_key=s.line_key,
                    relevance_score=score_map.get(s.line_key, 0.0),
                )
                for s in steps
                if s.line_key in kept_keys
            ][:max_steps]

    scored: list[tuple[ExtractedStep, float]] = []
    for step in steps:
        rel = score_step_relevance(step, query)
        scored.append(
            (
                ExtractedStep(
                    text=step.text,
                    source_index=step.source_index,
                    explicit_number=step.explicit_number,
                    temporal_rank=step.temporal_rank,
                    dependencies=step.dependencies,
                    line_key=step.line_key,
                    relevance_score=rel,
                ),
                rel,
            )
        )

    scored.sort(key=lambda pair: pair[1], reverse=True)
    score_by_key = {s.line_key: sc for s, sc in scored}
    above = [s for s, sc in scored if sc >= min_score]
    if len(above) >= min_keep:
        selected = above[:max_steps]
    else:
        selected = [s for s, _ in scored[:max_steps]]

    selected_keys = {s.line_key for s in selected}
    entities = _query_entities(query)
    for step in steps:
        if len(selected) >= max_steps:
            break
        if step.line_key in selected_keys:
            continue
        if entities and any(_entity_in_step(step.text, e) for e in entities[:5]):
            selected.append(step)
            selected_keys.add(step.line_key)

    return [
        ExtractedStep(
            text=s.text,
            source_index=s.source_index,
            explicit_number=s.explicit_number,
            temporal_rank=s.temporal_rank,
            dependencies=list(s.dependencies),
            line_key=s.line_key,
            relevance_score=score_by_key.get(s.line_key, 0.0),
        )
        for s in steps
        if s.line_key in selected_keys
    ]


def _step_sort_key(step: ExtractedStep) -> tuple:
    num = step.explicit_number if step.explicit_number is not None else 999
    return (num, step.temporal_rank, step.source_index)


def _build_dependency_edges(steps: list[ExtractedStep]) -> dict[int, set[int]]:
    """Map step index -> indices that must come before this step."""
    edges: dict[int, set[int]] = {i: set() for i in range(len(steps))}
    text_by_idx = {i: s.normalized_text() for i, s in enumerate(steps)}

    for i, step in enumerate(steps):
        for dep in step.dependencies:
            if dep == "__FIRST__":
                continue
            if dep.startswith("after:"):
                target = dep[6:]
                for j, other_text in text_by_idx.items():
                    if j != i and target[:30] in other_text:
                        edges[i].add(j)
            else:
                for j, other_text in text_by_idx.items():
                    if j != i and dep[:30] in other_text:
                        edges[j].add(i)
    return edges


def order_steps(steps: list[ExtractedStep], *, max_steps: int = 10) -> list[ExtractedStep]:
    """Sort steps using relevance, explicit numbering, temporal rank, dependencies."""
    if len(steps) <= 1:
        return steps[:max_steps]

    indexed = list(enumerate(steps))
    has_explicit = any(s.explicit_number is not None for _, s in indexed)

    if has_explicit:
        ordered = sorted(steps, key=_step_sort_key)
        return ordered[:max_steps]

    edges = _build_dependency_edges(steps)
    in_degree = {i: 0 for i in range(len(steps))}
    for i in range(len(steps)):
        for pred in edges[i]:
            in_degree[i] += 1

    queue = sorted(
        [i for i, deg in in_degree.items() if deg == 0],
        key=lambda idx: _step_sort_key(steps[idx]),
    )
    ordered_indices: list[int] = []

    while queue:
        idx = queue.pop(0)
        ordered_indices.append(idx)
        for j in range(len(steps)):
            if idx in edges[j]:
                in_degree[j] -= 1
                if in_degree[j] == 0:
                    queue.append(j)
        queue.sort(key=lambda i: _step_sort_key(steps[i]))

    if len(ordered_indices) < len(steps):
        remaining = [i for i in range(len(steps)) if i not in ordered_indices]
        remaining.sort(key=lambda i: _step_sort_key(steps[i]))
        ordered_indices.extend(remaining)

    return [steps[i] for i in ordered_indices][:max_steps]


def format_procedural_answer(steps: list[ExtractedStep]) -> str:
    """Format ordered steps with mandatory source citations."""
    if not steps:
        return ""

    lines: list[str] = []
    for i, step in enumerate(steps, start=1):
        lines.append(f"Step {i}: {step.text} [Source {step.source_index}]")
    return "\n\n".join(lines)


def build_procedural_prompt_section(steps: list[ExtractedStep]) -> str:
    """Evidence-backed step outline for LLM refinement."""
    if not steps:
        return ""
    lines = ["Extracted procedural evidence (preserve order and citations):"]
    for i, step in enumerate(steps, start=1):
        lines.append(f"  {i}. {step.text} [Source {step.source_index}]")
    return "\n".join(lines)


PROCEDURAL_SYSTEM_PROMPT = """You are a document-grounded technical assistant answering procedural questions.

Rules:
1. Answer ONLY from retrieved sources and the extracted step outline below.
2. Output ONLY numbered steps in this exact format:
   Step 1: <action> [Source N]
   Step 2: <action> [Source N]
3. Preserve the order of extracted steps unless sources explicitly reorder them.
4. Every step MUST end with [Source N] citing the supporting chunk.
5. Do not add steps not supported by sources.
6. If evidence is insufficient, respond exactly: "Insufficient retrieved evidence."
7. Do not use markdown code fences."""


def build_procedural_user_prompt(
    query: str,
    context: str,
    steps: list[ExtractedStep],
) -> str:
    outline = build_procedural_prompt_section(steps)
    return (
        f"Sources:\n{context}\n\n"
        f"{outline}\n\n"
        f"Question: {query}\n\n"
        "Produce an ordered procedural answer using the Step N: format with citations."
    )


def generate_procedural_answer_from_evidence(
    chunks: list[RetrievedChunk],
    query: str,
    *,
    min_steps: int = 1,
    max_steps: int = 10,
    relevance_threshold: float = 0.08,
) -> tuple[str, list[ExtractedStep]]:
    """
    Extract, filter by query relevance, order, and format procedural answer.

    Returns (formatted_answer, ordered_steps). Empty answer if insufficient steps.
    """
    extracted = extract_steps_from_chunks(chunks)
    filtered = filter_steps_by_relevance(
        extracted,
        query,
        max_steps=max_steps,
        min_score=relevance_threshold,
        min_keep=min_steps,
    )
    ordered = order_steps(filtered, max_steps=max_steps)
    if len(ordered) < min_steps:
        return "", ordered
    return format_procedural_answer(ordered), ordered
