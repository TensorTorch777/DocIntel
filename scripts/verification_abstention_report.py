#!/usr/bin/env python3
"""Report verification/refutation routing and abstention decisions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.claim_refutation import detect_claim_refutation  # noqa: E402
from app.services.evidence_sufficiency import assess_sufficiency, measure_coverage  # noqa: E402
from app.services.query_intent import classify_query_intent  # noqa: E402
from app.services.rag import RAGService  # noqa: E402
from app.services.vector_store import RetrievedChunk  # noqa: E402

BENCHMARKS = [
    {
        "id": "cr3_fault_address",
        "query": "Does CR3 store the faulting address during a page fault?",
        "chunks": [
            RetrievedChunk(
                chunk_id="cr2-fault",
                text=(
                    "The contents of the CR2 register. "
                    "The processor loads the CR2 register with the linear address "
                    "that generated the exception."
                ),
                page_number=3390,
                chunk_index=0,
                score=0.9,
                metadata={"rerank_score": 1.0},
            ),
            RetrievedChunk(
                chunk_id="pf",
                text="Page-fault exceptions (#PF; exception 14) are generated when...",
                page_number=3291,
                chunk_index=0,
                score=0.8,
                metadata={"rerank_score": 0.36},
            ),
        ],
        "expected_answer_prefix": "NO.",
    },
    {
        "id": "cr0_pg_validation",
        "query": "CR0.PG means Page Global Enable. Is this correct?",
        "chunks": [
            RetrievedChunk(
                chunk_id="cr0-pg",
                text="PG — Paging (bit 31 of CR0)",
                page_number=2100,
                chunk_index=0,
                score=0.9,
                metadata={"rerank_score": 1.0},
            ),
            RetrievedChunk(
                chunk_id="cr4-pge",
                text="PGE — Page Global Enable (bit 7 of CR4)",
                page_number=2101,
                chunk_index=0,
                score=0.9,
                metadata={"rerank_score": 0.9},
            ),
        ],
        "expected_answer_prefix": "NO.",
    },
    {
        "id": "cr2_pdbr_role",
        "query": "Is CR2 the page-directory base register?",
        "chunks": [
            RetrievedChunk(
                chunk_id="cr3-pdbr",
                text="CR3 — Page-Directory-Base Register (PDBR)",
                page_number=2500,
                chunk_index=0,
                score=0.9,
                metadata={"rerank_score": 0.95},
            ),
        ],
        "expected_answer_prefix": "NO.",
    },
]


def main() -> None:
    rows = []
    for case in BENCHMARKS:
        query = case["query"]
        chunks = case["chunks"]
        intent = classify_query_intent(query)
        coverage = measure_coverage(chunks, query)
        sufficiency = assess_sufficiency(chunks, query)
        refutation = detect_claim_refutation(chunks, query)
        final_answer = None
        if refutation:
            from app.models.schemas import RetrievedSource

            sources = [
                RetrievedSource(
                    source_index=i + 1,
                    chunk_id=c.chunk_id,
                    page_number=c.page_number,
                    vector_score=c.score,
                    rerank_score=float(c.metadata.get("rerank_score", c.score)),
                    excerpt=c.text[:200],
                )
                for i, c in enumerate(chunks)
            ]
            final_answer = RAGService._format_refutation_answer(refutation, sources)

        row = {
            "id": case["id"],
            "query": query,
            "detected_intent": intent.intent.value,
            "pipeline": intent.pipeline.value,
            "evidence_categories_required": list(intent.evidence_categories),
            "evidence_categories_matched": [
                cat
                for cat, score in coverage.to_dict().items()
                if cat.endswith("missing_categories") is False
                and isinstance(score, float)
                and score >= 0.5
                and cat
                not in ("query_relevance", "total_weighted", "procedural")
            ],
            "coverage": coverage.to_dict(),
            "abstention_decision": not sufficiency.sufficient,
            "confidence": sufficiency.confidence,
            "refutation_detected": refutation is not None,
            "final_answer": final_answer,
            "answer_template": intent.answer_template.value,
        }
        rows.append(row)

    out_json = ROOT / "docs" / "verification_abstention_report.json"
    out_md = ROOT / "docs" / "verification_abstention_report.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    lines = [
        "# Verification & Abstention Report",
        "",
        "| Case | Intent | Abstain? | Confidence | Refutation | Final answer |",
        "|------|--------|----------|------------|------------|--------------|",
    ]
    for r in rows:
        ans = (r["final_answer"] or "(gated)")[:80].replace("|", "/")
        lines.append(
            f"| {r['id']} | {r['detected_intent']} | "
            f"{'yes' if r['abstention_decision'] else 'no'} | {r['confidence']} | "
            f"{'yes' if r['refutation_detected'] else 'no'} | {ans} |"
        )
    lines.extend(["", "## Details", ""])
    for r in rows:
        lines.append(f"### {r['id']}")
        lines.append(f"**Query:** {r['query']}")
        lines.append(f"**Detected intent:** {r['detected_intent']} → {r['pipeline']}")
        lines.append(
            f"**Evidence required:** {', '.join(r['evidence_categories_required'])}"
        )
        lines.append(f"**Coverage:** {json.dumps(r['coverage'])}")
        lines.append(
            f"**Abstention decision:** {'ABSTAIN' if r['abstention_decision'] else 'PROCEED'}"
        )
        lines.append(f"**Answer template:** {r['answer_template']}")
        lines.append(f"**Final answer:** {r['final_answer'] or 'N/A'}")
        lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
