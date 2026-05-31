#!/usr/bin/env python3
"""Audit citation coverage across benchmark answers."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.citation_support import (
    citation_coverage_per_sentence,
    extract_cited_source_indices,
    extract_factual_sentences,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "benchmark" / "results" / "sprint3_full_516" / "benchmark_results.json"
DEFAULT_OUTPUT = ROOT / "benchmark" / "reports" / "citation_audit.md"


def _claim_cited(claim: str) -> bool:
    return bool(extract_cited_source_indices(claim))


def audit_case(result: dict) -> dict:
    answer = result.get("answer", "")
    claims = extract_factual_sentences(answer)
    cited = [c for c in claims if _claim_cited(c)]
    uncited = [c for c in claims if not _claim_cited(c)]
    coverage = citation_coverage_per_sentence(answer) if claims else 1.0

    return {
        "id": result["id"],
        "category": result.get("category"),
        "claims": len(claims),
        "cited_claims": len(cited),
        "uncited_claims": len(uncited),
        "coverage_pct": coverage * 100.0,
        "uncited_samples": uncited[:3],
        "abstained": result.get("abstained", False),
        "gated": result.get("gated", False),
    }


def audit(results_path: Path, output_path: Path) -> dict:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    case_results = results["case_results"]

    rows = [audit_case(r) for r in case_results if not r.get("gated")]
    total_claims = sum(r["claims"] for r in rows)
    total_cited = sum(r["cited_claims"] for r in rows)
    total_uncited = sum(r["uncited_claims"] for r in rows)
    overall_coverage = (total_cited / total_claims * 100.0) if total_claims else 100.0

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_cat[row["category"] or "unknown"].append(row)

    agg = results.get("aggregate", {})
    worst = sorted(rows, key=lambda r: (r["coverage_pct"], -r["uncited_claims"]))[:15]

    lines = [
        "# Citation Coverage Audit",
        "",
        f"**Source:** `{results_path.relative_to(ROOT)}`  ",
        f"**Cases audited:** {len(rows)} (excluding gated)",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Total factual claims | {total_claims} |",
        f"| Cited claims | {total_cited} |",
        f"| Uncited claims | {total_uncited} |",
        f"| Claim-level coverage | {overall_coverage:.1f}% |",
        f"| Benchmark citation_accuracy | {agg.get('citation_accuracy', 0):.1%} |",
        f"| Benchmark citation_coverage_per_sentence | {agg.get('citation_coverage_per_sentence', 0):.1%} |",
        "",
        "## Why citation accuracy is ~70%",
        "",
        "Citation accuracy combines **sentence coverage**, **valid source indices**, "
        "and **lexical alignment** with retrieved chunks. The ~70% headline reflects:",
        "",
        "1. **Uncited factual sentences** — especially in definition answers without "
        "per-sentence `[Source N]` tags.",
        "2. **Low definition_queries coverage** — procedural step templates cite better "
        "than free-form definitions.",
        "3. **Alignment penalty** — cited claims with weak token overlap to the "
        "referenced chunk reduce the composite score.",
        "",
        "## Coverage by category",
        "",
        "| Category | Cases | Claims | Cited | Coverage |",
        "|----------|------:|-------:|------:|---------:|",
    ]

    for cat in sorted(by_cat.keys()):
        items = by_cat[cat]
        c_claims = sum(i["claims"] for i in items)
        c_cited = sum(i["cited_claims"] for i in items)
        cov = (c_cited / c_claims * 100.0) if c_claims else 100.0
        lines.append(f"| {cat} | {len(items)} | {c_claims} | {c_cited} | {cov:.1f}% |")

    lines.extend(["", "## Worst coverage cases", ""])

    for row in worst:
        if row["uncited_claims"] == 0:
            continue
        lines.append(f"### `{row['id']}` ({row['category']}) — {row['coverage_pct']:.0f}%")
        lines.append("")
        lines.append(
            f"Claims: {row['claims']} | Cited: {row['cited_claims']} | "
            f"Uncited: {row['uncited_claims']}"
        )
        lines.append("")
        for sample in row["uncited_samples"]:
            lines.append(f"- _Uncited:_ {sample[:200]}")
        lines.append("")

    lines.extend(
        [
            "## Recommendations",
            "",
            "- Enforce **one citation per factual sentence** in QA prompts (already in "
            "conservative mode; extend to default QA).",
            "- Post-process answers to flag uncited sentences before returning.",
            "- Weight **citation_coverage_per_sentence** separately from alignment in "
            "dashboards for clearer tracking.",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "cases": len(rows),
        "total_claims": total_claims,
        "coverage_pct": overall_coverage,
        "output": str(output_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Citation coverage audit")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = audit(args.results, args.output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
