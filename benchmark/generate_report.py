#!/usr/bin/env python3
"""Generate a release-candidate benchmark report with plots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmark.visualize import generate_all_plots

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "benchmark" / "results" / "sprint3_full_516" / "benchmark_results.json"
DEFAULT_OUTPUT = ROOT / "benchmark" / "reports" / "benchmark_report.md"
PLOTS_DIR = ROOT / "benchmark" / "reports" / "plots"


def _pct(value: float) -> str:
    return f"{value:.1%}"


def _ms(value: float) -> str:
    return f"{value:.0f} ms"


def _rank_categories(by_category: dict) -> tuple[list[tuple], list[tuple]]:
    scored = []
    for cat, metrics in by_category.items():
        score = (
            metrics.get("must_contain_score", 0) * 0.4
            + metrics.get("retrieval_recall_at_k", 0) * 0.3
            + metrics.get("citation_accuracy", 0) * 0.2
            + (1.0 - metrics.get("hallucination_rate", 0)) * 0.1
        )
        scored.append((cat, score, metrics))
    scored.sort(key=lambda x: x[1], reverse=True)
    best = [(c, s, m) for c, s, m in scored[:3]]
    worst = [(c, s, m) for c, s, m in scored[-3:][::-1]]
    return best, worst


def generate_report(results_path: Path, output_path: Path, plots_dir: Path) -> Path:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    aggregate = results.get("aggregate", {})
    by_category = results.get("by_category", {})

    plot_files = generate_all_plots(results, plots_dir)
    plot_refs = [f"![{p}](plots/{p})" for p in plot_files]

    best, worst = _rank_categories(by_category)

    lines = [
        "# DocIntel Benchmark Report",
        "",
        f"**Document ID:** `{results.get('document_id')}`  ",
        f"**Timestamp:** {results.get('timestamp')}  ",
        f"**Cases:** {results.get('case_count', len(results.get('case_results', [])))}  ",
        f"**Pipeline:** Full (hybrid + rerank + definition resolver + evidence gate + verification)",
        "",
        "## Executive Summary",
        "",
        "DocIntel was evaluated on **516** technical RAG cases derived from Intel SDM–style "
        "register, procedure, adversarial, and abstention scenarios.",
        "",
        "| Metric | Result |",
        "|--------|-------:|",
        f"| Recall@K | {_pct(aggregate.get('retrieval_recall_at_k', 0))} |",
        f"| MRR | {aggregate.get('mrr', 0):.3f} |",
        f"| NDCG@K | {_pct(aggregate.get('ndcg_at_k', 0))} |",
        f"| Hallucination rate | {_pct(aggregate.get('hallucination_rate', 0))} |",
        f"| Citation accuracy | {_pct(aggregate.get('citation_accuracy', 0))} |",
        f"| Citation coverage / sentence | {_pct(aggregate.get('citation_coverage_per_sentence', 0))} |",
        f"| Abstention precision / recall | {_pct(aggregate.get('abstention_precision', 0))} / {_pct(aggregate.get('abstention_recall', 0))} |",
        f"| Avg latency | {_ms(aggregate.get('total_ms', 0))} |",
        "",
        "### Latency breakdown",
        "",
        f"- Retrieval: {_ms(aggregate.get('retrieval_ms', 0))}",
        f"- Rerank: {_ms(aggregate.get('rerank_ms', 0))}",
        f"- Generation: {_ms(aggregate.get('generation_ms', 0))}",
        f"- Verification: {_ms(aggregate.get('verification_ms', 0))}",
        "",
        "## Category Breakdown",
        "",
        "| Category | Recall@K | Must-contain | Hallucination | Citations |",
        "|----------|---------:|-------------:|--------------:|----------:|",
    ]

    for cat in sorted(by_category.keys()):
        m = by_category[cat]
        lines.append(
            f"| {cat} | {_pct(m.get('retrieval_recall_at_k', 0))} | "
            f"{_pct(m.get('must_contain_score', 0))} | "
            f"{_pct(m.get('hallucination_rate', 0))} | "
            f"{_pct(m.get('citation_accuracy', 0))} |"
        )

    lines.extend(["", "## Best Performing Categories", ""])
    for cat, score, m in best:
        lines.append(
            f"- **{cat}** — composite {score:.1%} "
            f"(recall {_pct(m.get('retrieval_recall_at_k', 0))}, "
            f"must-contain {_pct(m.get('must_contain_score', 0))})"
        )

    lines.extend(["", "## Weakest Categories", ""])
    for cat, score, m in worst:
        lines.append(
            f"- **{cat}** — composite {score:.1%} "
            f"(recall {_pct(m.get('retrieval_recall_at_k', 0))}, "
            f"must-contain {_pct(m.get('must_contain_score', 0))})"
        )

    lines.extend(
        [
            "",
            "## Recommendations",
            "",
            "1. **Definition queries** — improve per-sentence citations; relax evaluator "
            "synonyms or expand gold labels (see `definition_failures.md`).",
            "2. **Entity collision** — must-contain score is low; strengthen disambiguation "
            "prompts when multiple registers appear.",
            "3. **Procedural queries** — extra_step_rate remains high; continue query-aware "
            "step filtering tuning.",
            "4. **Citations** — target >85% sentence coverage (see `citation_audit.md`).",
            "5. **Latency** — verification skip rate ~50%; maintain selective verification "
            "for release.",
            "",
            "## Plots",
            "",
        ]
    )
    lines.extend(plot_refs)
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate benchmark report")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--plots-dir", type=Path, default=PLOTS_DIR)
    args = parser.parse_args()
    path = generate_report(args.results, args.output, args.plots_dir)
    print(f"Report written to {path}")


if __name__ == "__main__":
    main()
