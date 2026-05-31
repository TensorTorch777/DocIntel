#!/usr/bin/env python3
"""
DocIntel RAG benchmark runner.

Usage:
  python benchmark_runner.py --document-id <ID> [options]

Examples:
  python benchmark_runner.py --document-id abc123 --limit 10
  python benchmark_runner.py --document-id abc123 --compare-baselines
  python benchmark_runner.py --document-id abc123 --categories definition_queries
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.dependencies import get_rag_service  # noqa: E402
from app.models.schemas import BenchmarkRequest  # noqa: E402
from app.services.benchmark_framework import BenchmarkFramework  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("benchmark_runner")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DocIntel RAG benchmark suite")
    parser.add_argument("--document-id", required=True, help="Indexed document ID")
    parser.add_argument(
        "--cases",
        default=str(ROOT / "benchmark" / "benchmark_cases.json"),
        help="Path to benchmark_cases.json",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max cases to run")
    parser.add_argument(
        "--categories",
        nargs="*",
        default=None,
        help="Filter by category (e.g. definition_queries)",
    )
    parser.add_argument(
        "--compare-baselines",
        action="store_true",
        help="Run all four pipeline modes (A–D)",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip matplotlib plot generation",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "benchmark" / "results"),
        help="Directory for JSON/CSV exports",
    )
    parser.add_argument("--top-k", type=int, default=None, help="Retrieval top-k")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    rag = get_rag_service()
    framework = BenchmarkFramework(rag)

    request = BenchmarkRequest(
        document_id=args.document_id,
        cases_path=args.cases,
        categories=args.categories,
        limit=args.limit,
        compare_baselines=args.compare_baselines,
        generate_plots=not args.no_plots,
        output_dir=args.output_dir,
        top_k=args.top_k,
    )

    logger.info("Starting benchmark for document %s", args.document_id)
    result = await framework.run(request)

    print("\n=== DocIntel Benchmark Results ===")
    print(f"Document:     {result.document_id}")
    print(f"Cases run:    {result.case_count}")
    print(f"Aggregate:    {result.summary.aggregate_score:.1%}")
    print(f"Recall@k:     {result.summary.retrieval_recall_at_k:.1%}")
    print(f"MRR:          {result.summary.mrr:.3f}")
    print(f"Hallucination:{result.summary.hallucination_rate:.1%}")
    print(f"Abstention P/R:{result.summary.abstention_precision:.1%} / {result.summary.abstention_recall:.1%}")
    print(f"Avg latency:  {result.summary.total_ms:.0f} ms")
    print(f"JSON:         {result.results_json}")
    print(f"CSV:          {result.results_csv}")
    if result.plot_files:
        print(f"Plots:        {', '.join(result.plot_files)}")

    if result.mode_comparison:
        print("\n--- Pipeline comparison ---")
        for mode, metrics in result.mode_comparison.items():
            print(
                f"  {mode}: recall={metrics.get('retrieval_recall_at_k', 0):.1%} "
                f"halluc={metrics.get('hallucination_rate', 0):.1%} "
                f"latency={metrics.get('total_ms', 0):.0f}ms"
            )

    print("\n--- Category breakdown ---")
    for cat, metrics in sorted(result.by_category.items()):
        print(
            f"  {cat}: recall={metrics.get('retrieval_recall_at_k', 0):.1%} "
            f"must_contain={metrics.get('must_contain_score', 0):.1%}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
