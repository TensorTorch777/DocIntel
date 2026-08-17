#!/usr/bin/env python3
"""Semantic embedding retrieval benchmark (cosine similarity on labeled pairs).

Offline evaluation: embed queries and candidate passages, rank by cosine
similarity (L2-normalized vectors, matching production Chroma settings),
and report Recall@k, MRR, and per-case diagnostics.

No indexed PDF required — uses hand-labeled Intel SDM-style query/chunk pairs
aligned with the project's verification and intent benchmarks.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.services.embedding import EmbeddingService  # noqa: E402

# Shared distractor passages (hard negatives — same domain, wrong answer)
DISTRACTORS: dict[str, str] = {
    "cr2-fault": (
        "7-46 Vol. 3A INTERRUPT AND EXCEPTION HANDLING • The contents of the CR2 register. "
        "The processor loads the CR2 register with the linear address that generated the exception."
    ),
    "cr3-pdbr": "CR3 — Page-Directory-Base Register (PDBR)",
    "cr0-pg": "PG — Paging (bit 31 of CR0)",
    "cr4-pge": "PGE — Page Global Enable (bit 7 of CR4)",
    "pf-generic": (
        "Page-fault exceptions (#PF; exception 14) are generated when linear address "
        "translation fails or protection checks fail during a memory access."
    ),
    "gp-generic": (
        "General-protection exceptions (#GP; exception 13) are generated for "
        "privilege violations and invalid operations in protected mode."
    ),
    "nxe-def": (
        "IA32_EFER.NXE [bit 11] — Execute Disable Enable. When IA32_EFER.NXE=1, "
        "execute-disable protection is enabled if paging is enabled and CR4.PAE=1."
    ),
    "ia32e-procedure": (
        "To enter IA-32e mode: enable PAE (CR4.PAE), set LME (IA32_EFER.LME), "
        "enable paging (CR0.PG), then perform a far jump to 64-bit code segment."
    ),
    "real-mode-intro": (
        "In real-address mode after reset, the processor begins execution at "
        "FFFF_FFF0h with CS.base = FFFF0000h and IP = FFF0h."
    ),
    "cr0-reset": (
        "Following reset, CR0 is set to 60000010H — PE is cleared (real-address mode), "
        "PG is cleared (paging disabled), and WP is set."
    ),
    "paging-overview": (
        "When paging is enabled (CR0.PG=1), linear addresses are translated through "
        "page tables referenced by CR3."
    ),
    "cr4-pae": "PAE — Physical Address Extension (bit 5 of CR4)",
}

# Labeled benchmark: query → one or more gold chunk ids (any gold in top-k counts)
BENCHMARK_CASES: list[dict] = [
    {
        "id": "cr3_fault_address",
        "query": "Does CR3 store the faulting address during a page fault?",
        "gold_ids": ["cr2-fault"],
        "candidate_ids": ["cr2-fault", "cr3-pdbr", "pf-generic", "paging-overview"],
        "notes": "Gold explains CR2 holds faulting linear address, not CR3",
    },
    {
        "id": "cr0_pg_validation",
        "query": "CR0.PG means Page Global Enable. Is this correct?",
        "gold_ids": ["cr0-pg", "cr4-pge"],
        "candidate_ids": ["cr0-pg", "cr4-pge", "cr4-pae", "paging-overview"],
        "notes": "Both PG and PGE definitions needed to refute conflation",
    },
    {
        "id": "cr2_pdbr_role",
        "query": "Is CR2 the page-directory base register?",
        "gold_ids": ["cr3-pdbr"],
        "candidate_ids": ["cr3-pdbr", "cr2-fault", "paging-overview", "cr0-pg"],
        "notes": "CR3 is PDBR, not CR2",
    },
    {
        "id": "compare_pg_pge",
        "query": "Differentiate CR0.PG and CR4.PGE — what does each bit enable?",
        "gold_ids": ["cr0-pg", "cr4-pge"],
        "candidate_ids": ["cr0-pg", "cr4-pge", "cr4-pae", "paging-overview", "gp-generic"],
        "notes": "Comparison requires both authoritative definitions",
    },
    {
        "id": "cr0_pg_definition",
        "query": "What is the meaning of CR0.PG?",
        "gold_ids": ["cr0-pg"],
        "candidate_ids": ["cr0-pg", "cr4-pge", "paging-overview", "cr4-pae"],
        "notes": "Pure definition lookup",
    },
    {
        "id": "nxe_gp_hallucination",
        "query": "Does setting NXE always cause a #GP fault regardless of paging mode?",
        "gold_ids": ["nxe-def"],
        "candidate_ids": ["nxe-def", "gp-generic", "pf-generic", "paging-overview"],
        "notes": "NXE behavior is conditional on paging/PAE, not unconditional #GP",
    },
    {
        "id": "ia32e_transition",
        "query": "Explain the sequence required to transition from real-address mode to IA-32e mode.",
        "gold_ids": ["ia32e-procedure"],
        "candidate_ids": [
            "ia32e-procedure",
            "real-mode-intro",
            "cr0-reset",
            "paging-overview",
            "cr4-pae",
        ],
        "notes": "Procedural sequence, not reset state alone",
    },
    {
        "id": "cr0_reset_lookup",
        "query": "What is the default value of CR0 when the processor is reset?",
        "gold_ids": ["cr0-reset"],
        "candidate_ids": ["cr0-reset", "real-mode-intro", "cr0-pg", "paging-overview"],
        "notes": "Lookup for reset value",
    },
]


@dataclass
class CaseResult:
    id: str
    query: str
    gold_ids: list[str]
    best_gold_rank: int | None
    recall_at_1: bool
    recall_at_3: bool
    reciprocal_rank: float
    gold_cosine_mean: float
    distractor_cosine_mean: float
    margin: float
    rankings: list[dict]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Dot product for L2-normalized vectors (= cosine similarity)."""
    return sum(x * y for x, y in zip(a, b, strict=True))


def cosine_similarity_raw(a: list[float], b: list[float]) -> float:
    """Cosine similarity without assuming normalization."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def evaluate_case(
    case: dict,
    query_vec: list[float],
    chunk_vecs: dict[str, list[float]],
    *,
    normalized: bool,
) -> CaseResult:
    gold_set = set(case["gold_ids"])
    sim_fn = cosine_similarity if normalized else cosine_similarity_raw

    scored: list[tuple[str, float]] = []
    for cid in case["candidate_ids"]:
        scored.append((cid, sim_fn(query_vec, chunk_vecs[cid])))
    scored.sort(key=lambda x: x[1], reverse=True)

    ranks = [i + 1 for i, (cid, _) in enumerate(scored) if cid in gold_set]
    best_rank = min(ranks) if ranks else None
    rr = 1.0 / best_rank if best_rank else 0.0

    gold_sims = [sim_fn(query_vec, chunk_vecs[cid]) for cid in case["gold_ids"]]
    distractor_ids = [cid for cid in case["candidate_ids"] if cid not in gold_set]
    distractor_sims = [sim_fn(query_vec, chunk_vecs[cid]) for cid in distractor_ids]

    gold_mean = sum(gold_sims) / len(gold_sims) if gold_sims else 0.0
    dist_mean = sum(distractor_sims) / len(distractor_sims) if distractor_sims else 0.0

    return CaseResult(
        id=case["id"],
        query=case["query"],
        gold_ids=case["gold_ids"],
        best_gold_rank=best_rank,
        recall_at_1=best_rank == 1 if best_rank else False,
        recall_at_3=best_rank is not None and best_rank <= 3,
        reciprocal_rank=rr,
        gold_cosine_mean=round(gold_mean, 4),
        distractor_cosine_mean=round(dist_mean, 4),
        margin=round(gold_mean - dist_mean, 4),
        rankings=[
            {"chunk_id": cid, "cosine": round(score, 4), "is_gold": cid in gold_set}
            for cid, score in scored
        ],
    )


def aggregate(results: list[CaseResult]) -> dict:
    n = len(results)
    return {
        "cases": n,
        "recall_at_1": round(sum(r.recall_at_1 for r in results) / n, 4),
        "recall_at_3": round(sum(r.recall_at_3 for r in results) / n, 4),
        "mrr": round(sum(r.reciprocal_rank for r in results) / n, 4),
        "mean_gold_cosine": round(sum(r.gold_cosine_mean for r in results) / n, 4),
        "mean_distractor_cosine": round(
            sum(r.distractor_cosine_mean for r in results) / n, 4
        ),
        "mean_margin": round(sum(r.margin for r in results) / n, 4),
    }


def render_markdown(report: dict) -> str:
    agg = report["aggregate"]
    lines = [
        "# Semantic Embedding Benchmark",
        "",
        f"**Model:** `{report['embedding_model']}`  ",
        f"**Metric:** cosine similarity ({report['vector_mode']})  ",
        f"**Cases:** {agg['cases']}",
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Recall@1 | {agg['recall_at_1']:.1%} |",
        f"| Recall@3 | {agg['recall_at_3']:.1%} |",
        f"| MRR | {agg['mrr']:.4f} |",
        f"| Mean gold cosine | {agg['mean_gold_cosine']:.4f} |",
        f"| Mean distractor cosine | {agg['mean_distractor_cosine']:.4f} |",
        f"| Mean gold − distractor margin | {agg['mean_margin']:.4f} |",
        "",
        "## Per-case results",
        "",
        "| Case | Best gold rank | R@1 | R@3 | Gold cos | Dist cos | Margin |",
        "|------|----------------|-----|-----|----------|----------|--------|",
    ]
    for r in report["cases"]:
        lines.append(
            f"| {r['id']} | {r['best_gold_rank'] or '—'} | "
            f"{'✓' if r['recall_at_1'] else '✗'} | "
            f"{'✓' if r['recall_at_3'] else '✗'} | "
            f"{r['gold_cosine_mean']:.3f} | {r['distractor_cosine_mean']:.3f} | "
            f"{r['margin']:+.3f} |"
        )

    lines.extend(["", "## Rankings", ""])
    for r in report["cases"]:
        lines.append(f"### {r['id']}")
        lines.append(f"**Query:** {r['query']}")
        for item in r["rankings"]:
            mark = " **GOLD**" if item["is_gold"] else ""
            lines.append(f"- `{item['chunk_id']}` — cosine {item['cosine']:.4f}{mark}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    settings = get_settings()
    embedder = EmbeddingService(settings)

    all_texts: list[str] = []
    text_to_id: dict[str, str] = {}
    for cid, text in DISTRACTORS.items():
        text_to_id[text] = cid
        all_texts.append(text)

    unique_texts = list(dict.fromkeys(all_texts))
    vectors = embedder.embed_texts(unique_texts)
    chunk_vecs = {text_to_id[t]: v for t, v in zip(unique_texts, vectors, strict=True)}

    case_results: list[CaseResult] = []
    for case in BENCHMARK_CASES:
        q_vec = embedder.embed_query(case["query"])
        case_results.append(
            evaluate_case(case, q_vec, chunk_vecs, normalized=True)
        )

    report = {
        "embedding_model": settings.embedding_model,
        "vector_mode": "L2-normalized (production — matches Chroma hnsw:space=cosine)",
        "aggregate": aggregate(case_results),
        "cases": [asdict(r) for r in case_results],
    }

    out_json = ROOT / "docs" / "embedding_semantic_benchmark.json"
    out_md = ROOT / "docs" / "embedding_semantic_benchmark.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = render_markdown(report)
    out_md.write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
