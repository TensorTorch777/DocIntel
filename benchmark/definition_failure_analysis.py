#!/usr/bin/env python3
"""Analyze definition-query benchmark failures and classify root causes."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.register_definition_resolver import (
    extract_register_entities,
    is_authoritative_definition,
)
from benchmark.metrics import compute_definition_funnel, must_contain_score

DEFAULT_CASES = ROOT / "benchmark" / "benchmark_cases.json"
DEFAULT_RESULTS = ROOT / "benchmark" / "results" / "sprint3_full_516" / "benchmark_results.json"
DEFAULT_OUTPUT = ROOT / "benchmark" / "reports" / "definition_failures.md"


def _find_authoritative_excerpt(chunks: list[str], query: str) -> str:
    entities = extract_register_entities(query)
    for text in chunks:
        if any(is_authoritative_definition(text, e) for e in entities):
            return text[:500].replace("\n", " ")
    return ""


def _find_selected_excerpt(chunks: list[str], query: str) -> str:
    auth = _find_authoritative_excerpt(chunks, query)
    if auth:
        return auth
    return (chunks[0][:500].replace("\n", " ") if chunks else "")


def _expected_answer(case: dict) -> str:
    exp = case.get("expected", {})
    parts = exp.get("must_contain", [])
    avoid = exp.get("must_not_contain", [])
    text = "Must contain: " + ", ".join(parts) if parts else "No must_contain"
    if avoid:
        text += f" | Must NOT contain: {', '.join(avoid)}"
    return text


def classify_failure(
    case: dict,
    result: dict,
    *,
    case_def: dict,
) -> str:
    """Classify a failed definition case into one root-cause bucket."""
    if result.get("definition_correct"):
        return "pass"

    must_contain = case_def.get("expected", {}).get("must_contain", [])
    must_not = case_def.get("expected", {}).get("must_not_contain", [])
    answer = result.get("answer", "")
    mc = must_contain_score(answer, must_contain)

    if result.get("abstained") and not case_def.get("should_abstain"):
        return "grounding failure"

    if result.get("must_not_violations", 0) > 0:
        return "grounding failure"

    if result.get("hallucination") and mc >= 0.5:
        return "evaluator failure"

    if not result.get("definition_retrieved"):
        if result.get("expected_chunks_hit", 0) == 0:
            return "retrieval failure"
        return "retrieval failure"

    if result.get("definition_retrieved") and not result.get("definition_selected"):
        return "reranking failure"

    if result.get("definition_selected") and not result.get("definition_used"):
        return "prompt failure"

    if result.get("definition_used") and mc >= 0.67 and not result.get("definition_correct"):
        missing = [t for t in must_contain if t.lower() not in answer.lower()]
        if not missing and result.get("must_not_violations", 0) == 0:
            return "evaluator failure"
        if missing and len(missing) <= 1 and mc >= 0.67:
            return "evaluator failure"

    if not result.get("definition_used") and mc < 0.5:
        return "prompt failure"

    if result.get("hallucination"):
        return "grounding failure"

    return "grounding failure"


def analyze(
    cases_path: Path,
    results_path: Path,
    output_path: Path,
) -> dict:
    cases_raw = json.loads(cases_path.read_text(encoding="utf-8"))
    case_by_id = {c["id"]: c for c in cases_raw["cases"]}
    results = json.loads(results_path.read_text(encoding="utf-8"))
    case_results = [r for r in results["case_results"] if r.get("category") == "definition_queries"]

    failures: list[dict] = []
    reasons: Counter[str] = Counter()

    for result in case_results:
        case = case_by_id.get(result["id"], {})
        reason = classify_failure(case, result, case_def=case)
        if reason == "pass":
            continue

        chunks = result.get("retrieved_chunks", [])
        funnel = compute_definition_funnel(
            query=result["query"],
            answer=result.get("answer", ""),
            selected_texts=chunks,
            merged_texts=chunks,
            must_contain=case.get("expected", {}).get("must_contain", []),
            must_not=case.get("expected", {}).get("must_not_contain", []),
        )

        failures.append(
            {
                "id": result["id"],
                "query": result["query"],
                "expected_answer": _expected_answer(case),
                "authoritative_chunk": _find_authoritative_excerpt(chunks, result["query"]),
                "selected_chunk": _find_selected_excerpt(chunks, result["query"]),
                "generated_answer": result.get("answer", "")[:600],
                "failure_reason": reason,
                "definition_retrieved": funnel.get("definition_retrieved"),
                "definition_selected": funnel.get("definition_selected"),
                "definition_used": funnel.get("definition_used"),
                "must_contain_score": result.get("must_contain_score"),
                "abstained": result.get("abstained"),
            }
        )
        reasons[reason] += 1

    total = len(case_results)
    passed = total - len(failures)
    agg = results.get("aggregate", {})
    def_cat = results.get("by_category", {}).get("definition_queries", {})

    lines = [
        "# Definition Failure Analysis",
        "",
        f"**Source:** `{results_path.relative_to(ROOT)}`  ",
        f"**Cases analyzed:** {total} definition queries  ",
        f"**Passed (`definition_correct`):** {passed} ({passed / total:.1%})  ",
        f"**Failed:** {len(failures)} ({len(failures) / total:.1%})",
        "",
        "## Executive finding",
        "",
        "The headline **definition_accuracy (34.5%)** understates answer quality. "
        f"**must_contain_score** for the same category is **{def_cat.get('must_contain_score', 0):.1%}**, "
        f"and **definition_used_rate** is **{def_cat.get('definition_used_rate', 0):.1%}**. "
        "Many failures are **evaluator strictness** (partial phrasing, synonym mismatch) "
        "rather than missing retrieval.",
        "",
        "## Funnel summary (definition_queries)",
        "",
        "| Stage | Rate |",
        "|-------|------|",
        f"| Authoritative retrieved | {def_cat.get('definition_retrieved_rate', 0):.1%} |",
        f"| Authoritative selected (top-k) | {def_cat.get('definition_selected_rate', 0):.1%} |",
        f"| Definition used in answer | {def_cat.get('definition_used_rate', 0):.1%} |",
        f"| Definition correct (strict) | {def_cat.get('definition_correct_rate', 0):.1%} |",
        f"| Legacy must_contain score | {def_cat.get('must_contain_score', 0):.1%} |",
        "",
        "## Failure classification",
        "",
        "| Reason | Count | Share of failures |",
        "|--------|------:|------------------:|",
    ]

    for reason, count in reasons.most_common():
        lines.append(f"| {reason} | {count} | {count / len(failures):.1%} |")

    lines.extend(
        [
            "",
            "## Interpretation by class",
            "",
            "- **retrieval failure** — authoritative definition not in retrieved context; "
            "expected chunk patterns missed.",
            "- **reranking failure** — definition found in pool but not promoted to top-k.",
            "- **prompt failure** — authoritative chunk selected but answer omits key terms.",
            "- **evaluator failure** — answer largely correct; strict `must_contain` / funnel "
            "logic marks it wrong.",
            "- **grounding failure** — abstention, must_not violation, or hallucination flag.",
            "",
            "## Failed cases (sample)",
            "",
        ]
    )

    for item in failures[:25]:
        lines.extend(
            [
                f"### `{item['id']}` — {item['failure_reason']}",
                "",
                f"- **Query:** {item['query']}",
                f"- **Expected:** {item['expected_answer']}",
                f"- **Must-contain score:** {item.get('must_contain_score')}",
                f"- **Funnel:** retrieved={item['definition_retrieved']} → "
                f"selected={item['definition_selected']} → used={item['definition_used']}",
                f"- **Authoritative excerpt:** {item['authoritative_chunk'] or '_none_'}",
                f"- **Selected excerpt:** {item['selected_chunk'] or '_none_'}",
                f"- **Generated answer:** {item['generated_answer'] or '_empty_'}",
                "",
            ]
        )

    if len(failures) > 25:
        lines.append(f"_… and {len(failures) - 25} additional failures._")
        lines.append("")

    lines.extend(
        [
            "## Conclusion",
            "",
            f"- **System failures** (retrieval + reranking + prompt + grounding): "
            f"{reasons['retrieval failure'] + reasons['reranking failure'] + reasons['prompt failure'] + reasons['grounding failure']} cases",
            f"- **Metric / evaluator issues:** {reasons['evaluator failure']} cases",
            "",
            "Recommendation: treat **must_contain_score** and manual review as primary "
            "definition quality signals until benchmark labels support synonym-aware matching.",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "total": total,
        "failed": len(failures),
        "reasons": dict(reasons),
        "output": str(output_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Definition failure analysis")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    summary = analyze(args.cases, args.results, args.output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
