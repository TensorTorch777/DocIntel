#!/usr/bin/env python3
"""Generate query-intent routing report for benchmark-style test queries."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.evidence_sufficiency import _required_categories  # noqa: E402
from app.services.procedural_reasoning import is_procedural_query  # noqa: E402
from app.services.query_intent import classify_query_intent  # noqa: E402

TEST_QUERIES = [
    {
        "id": "definition_validation",
        "query": "CR0.PG means Page Global Enable. Is this correct?",
        "expected_intent": "verification",
        "expected_pipeline": "verification_qa",
        "notes": "Should answer NO: CR0.PG=Paging Enable; CR4.PGE=Page Global Enable",
    },
    {
        "id": "compare_entities",
        "query": "Differentiate CR0.PG and CR4.PGE — what does each bit enable?",
        "expected_intent": "comparison",
        "expected_pipeline": "comparison_qa",
        "notes": "One definition per bit with citations",
    },
    {
        "id": "procedural_sequence",
        "query": "Explain the sequence required to transition from real-address mode to IA-32e mode.",
        "expected_intent": "procedural",
        "expected_pipeline": "procedural_extraction",
        "notes": "Gate on procedural+behavior evidence, not definition-only",
    },
    {
        "id": "hallucination_resistance",
        "query": "Does setting NXE always cause a #GP fault regardless of paging mode?",
        "expected_intent": "verification",
        "expected_pipeline": "verification_qa",
        "notes": "Conservative yes/no with source-backed exception behavior",
    },
]


def main() -> None:
    rows = []
    for case in TEST_QUERIES:
        query = case["query"]
        intent = classify_query_intent(query)
        required = sorted(_required_categories(query))
        row = {
            **case,
            "detected_intent": intent.intent.value,
            "selected_pipeline": intent.pipeline.value,
            "evidence_categories_required": required,
            "answer_template": intent.answer_template.value,
            "procedural_flag_legacy": is_procedural_query(query),
            "classification_reasons": list(intent.reasons),
            "intent_match": intent.intent.value == case["expected_intent"],
        }
        rows.append(row)

    out_json = ROOT / "docs" / "query_intent_routing_report.json"
    out_md = ROOT / "docs" / "query_intent_routing_report.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    lines = [
        "# Query Intent Routing Report",
        "",
        "| Case | Detected intent | Pipeline | Evidence required | Answer template | Match |",
        "|------|-----------------|----------|-------------------|-----------------|-------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['detected_intent']} | {r['selected_pipeline']} | "
            f"{', '.join(r['evidence_categories_required'])} | {r['answer_template']} | "
            f"{'✓' if r['intent_match'] else '✗'} |"
        )
    lines.extend(["", "## Details", ""])
    for r in rows:
        lines.append(f"### {r['id']}")
        lines.append(f"**Query:** {r['query']}")
        lines.append(f"**Expected:** {r['expected_intent']} → {r['expected_pipeline']}")
        lines.append(f"**Detected:** {r['detected_intent']} → {r['selected_pipeline']}")
        lines.append(f"**Evidence categories:** {', '.join(r['evidence_categories_required'])}")
        lines.append(f"**Answer template:** {r['answer_template']}")
        lines.append(f"**Reasons:** {', '.join(r['classification_reasons'])}")
        lines.append(f"**Notes:** {r['notes']}")
        lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
