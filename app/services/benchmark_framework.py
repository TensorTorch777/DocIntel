"""Comprehensive RAG benchmark runner with metrics, baselines, and exports."""

from __future__ import annotations

import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models.schemas import (
    BenchmarkCaseDefinition,
    BenchmarkDataset,
    BenchmarkRequest,
    BenchmarkResponse,
    BenchmarkRunSummary,
)
from app.services.rag import RAGService
from benchmark.metrics import (
    CaseMetrics,
    LatencyMetrics,
    aggregate_by_category,
    aggregate_metrics,
    compute_case_metrics,
)
from benchmark.pipeline import ALL_MODES, PipelineConfig, PipelineMode
from benchmark.visualize import generate_all_plots

logger = logging.getLogger(__name__)

DEFAULT_CASES_PATH = Path(__file__).resolve().parents[2] / "benchmark" / "benchmark_cases.json"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "benchmark" / "results"
PLOTS_DIR = Path(__file__).resolve().parents[2] / "benchmark" / "plots"


def load_benchmark_dataset(path: Path | None = None) -> BenchmarkDataset:
    cases_path = path or DEFAULT_CASES_PATH
    raw = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = [BenchmarkCaseDefinition.model_validate(c) for c in raw["cases"]]
    return BenchmarkDataset(
        version=raw.get("version", "1.0"),
        description=raw.get("description", ""),
        categories=raw.get("categories", []),
        case_count=len(cases),
        cases=cases,
    )


class BenchmarkFramework:
    """Run benchmark cases, compute metrics, export results, generate plots."""

    def __init__(self, rag_service: RAGService) -> None:
        self._rag = rag_service
        self._settings = get_settings()

    async def run(self, request: BenchmarkRequest) -> BenchmarkResponse:
        dataset = load_benchmark_dataset(
            Path(request.cases_path) if request.cases_path else None
        )
        cases = self._filter_cases(dataset.cases, request)

        modes = self._parse_modes(request.modes)
        if request.compare_baselines:
            modes = list(ALL_MODES)

        output_dir = Path(request.output_dir) if request.output_dir else DEFAULT_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        all_case_results: list[dict[str, Any]] = []
        mode_comparison: dict[str, dict[str, float]] = {}

        for mode in modes:
            pipeline = PipelineConfig.from_mode(mode)
            mode_label = pipeline.label
            logger.info("Benchmark mode %s — %d cases", mode_label, len(cases))

            for i, case in enumerate(cases):
                if i and i % 25 == 0:
                    logger.info("  progress: %d / %d", i, len(cases))
                row = await self._run_case(
                    request.document_id,
                    case,
                    pipeline=pipeline,
                    mode=mode.value,
                    mode_label=mode_label,
                    top_k=request.top_k,
                )
                all_case_results.append(row)

            mode_rows = [r for r in all_case_results if r["pipeline_mode"] == mode.value]
            mode_comparison[mode_label] = aggregate_metrics(mode_rows)

        # Primary mode results for dashboard (prefer FULL)
        primary_mode = PipelineMode.FULL.value
        if not any(r["pipeline_mode"] == primary_mode for r in all_case_results):
            primary_mode = modes[-1].value
        primary_results = [r for r in all_case_results if r["pipeline_mode"] == primary_mode]

        aggregate = aggregate_metrics(primary_results)
        by_category = aggregate_by_category(primary_results)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        results_payload = {
            "document_id": request.document_id,
            "timestamp": timestamp,
            "case_count": len(primary_results),
            "modes": [m.value for m in modes],
            "aggregate": aggregate,
            "by_category": by_category,
            "mode_comparison": mode_comparison,
            "case_results": all_case_results if request.compare_baselines else primary_results,
        }

        json_path = output_dir / "benchmark_results.json"
        csv_path = output_dir / "benchmark_results.csv"
        json_path.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
        self._export_csv(all_case_results if request.compare_baselines else primary_results, csv_path)

        plot_files: list[str] = []
        if request.generate_plots:
            PLOTS_DIR.mkdir(parents=True, exist_ok=True)
            plot_files = generate_all_plots(results_payload, PLOTS_DIR)

        best, worst = self._rank_cases(primary_results)

        return BenchmarkResponse(
            document_id=request.document_id,
            timestamp=timestamp,
            case_count=len(primary_results),
            modes=[m.value for m in modes],
            summary=BenchmarkRunSummary(
                aggregate_score=self._composite_score(aggregate),
                retrieval_recall_at_k=aggregate.get("retrieval_recall_at_k", 0),
                mrr=aggregate.get("mrr", 0),
                ndcg_at_k=aggregate.get("ndcg_at_k", 0),
                definition_accuracy=aggregate.get("definition_accuracy", 0),
                hallucination_rate=aggregate.get("hallucination_rate", 0),
                unsupported_claim_ratio=aggregate.get("unsupported_claim_ratio", 0),
                abstention_precision=aggregate.get("abstention_precision", 0),
                abstention_recall=aggregate.get("abstention_recall", 0),
                stepwise_accuracy=aggregate.get("stepwise_accuracy", 0),
                ordered_step_accuracy=aggregate.get("ordered_step_accuracy", 0),
                missing_step_rate=aggregate.get("missing_step_rate", 0),
                extra_step_rate=aggregate.get("extra_step_rate", 0),
                step_precision=aggregate.get("step_precision", 0),
                step_recall=aggregate.get("step_recall", 0),
                citation_accuracy=aggregate.get("citation_accuracy", 0),
                citation_coverage_per_sentence=aggregate.get("citation_coverage_per_sentence", 0),
                definition_retrieved_rate=aggregate.get("definition_retrieved_rate", 0),
                definition_selected_rate=aggregate.get("definition_selected_rate", 0),
                definition_used_rate=aggregate.get("definition_used_rate", 0),
                definition_correct_rate=aggregate.get("definition_correct_rate", 0),
                retrieval_ms=aggregate.get("retrieval_ms", 0),
                rerank_ms=aggregate.get("rerank_ms", 0),
                generation_ms=aggregate.get("generation_ms", 0),
                verification_ms=aggregate.get("verification_ms", 0),
                total_ms=aggregate.get("total_ms", 0),
            ),
            by_category=by_category,
            mode_comparison=mode_comparison,
            best_cases=best,
            worst_cases=worst,
            plot_files=plot_files,
            results_json=str(json_path),
            results_csv=str(csv_path),
            case_results=primary_results[: request.dashboard_case_limit],
        )

    async def _run_case(
        self,
        document_id: str,
        case: BenchmarkCaseDefinition,
        *,
        pipeline: PipelineConfig,
        mode: str,
        mode_label: str,
        top_k: int | None,
    ) -> dict[str, Any]:
        k = top_k or self._settings.retrieval_top_k
        run = await self._rag.evaluate_query(
            document_id, case.query, pipeline=pipeline, top_k=top_k
        )

        latency = LatencyMetrics(**run["latency"])
        metrics: CaseMetrics = compute_case_metrics(
            query=case.query,
            answer=run["answer"],
            retrieved_texts=run["retrieved_chunks"],
            expected=case.expected.model_dump(),
            expected_chunks=case.expected_chunks,
            should_abstain=case.should_abstain,
            expected_ordered_steps=case.expected_ordered_steps,
            category=case.category,
            verification=run.get("verification"),
            gated=run.get("gated", False),
            has_sources=bool(run.get("retrieved_chunks")),
            k=k,
            latency=latency,
            merged_retrieved_texts=run.get("merged_retrieved_chunks"),
        )

        return {
            "id": case.id,
            "category": case.category,
            "query": case.query,
            "pipeline_mode": mode,
            "pipeline_label": mode_label,
            "should_abstain": case.should_abstain,
            "answer": run["answer"],
            "answer_preview": run["answer"][:400],
            "gated": run.get("gated", False),
            "abstained": metrics.abstained,
            "abstention_correct": metrics.abstention_correct,
            "hallucination": metrics.hallucination,
            "retrieved_chunks": run["retrieved_chunks"],
            "chunk_ids": run["chunk_ids"],
            "rerank_scores": run["rerank_scores"],
            "sources": run["sources"],
            "retrieval_confidence": run["retrieval_confidence"],
            "evidence_sufficiency": run["evidence_sufficiency"],
            "verification": run.get("verification"),
            "retrieval_recall_at_k": metrics.retrieval_recall_at_k,
            "mrr": metrics.mrr,
            "ndcg_at_k": metrics.ndcg_at_k,
            "definition_accuracy": metrics.definition_accuracy,
            "unsupported_claim_ratio": metrics.unsupported_claim_ratio,
            "stepwise_accuracy": metrics.stepwise_accuracy,
            "ordered_step_accuracy": metrics.ordered_step_accuracy,
            "missing_step_rate": metrics.missing_step_rate,
            "extra_step_rate": metrics.extra_step_rate,
            "step_precision": metrics.step_precision,
            "step_recall": metrics.step_recall,
            "citation_accuracy": metrics.citation_accuracy,
            "citation_coverage_per_sentence": metrics.citation_coverage_per_sentence,
            "definition_retrieved": metrics.definition_retrieved,
            "definition_selected": metrics.definition_selected,
            "definition_used": metrics.definition_used,
            "definition_correct": metrics.definition_correct,
            "verification_skipped": run.get("verification_skipped", False),
            "verification_skip_reason": run.get("verification_skip_reason", ""),
            "must_contain_score": metrics.must_contain_score,
            "must_not_violations": metrics.must_not_violations,
            "expected_chunks_hit": metrics.expected_chunks_hit,
            "expected_chunks_total": metrics.expected_chunks_total,
            "retrieval_ms": latency.retrieval_ms,
            "rerank_ms": latency.rerank_ms,
            "generation_ms": latency.generation_ms,
            "verification_ms": latency.verification_ms,
            "total_ms": latency.total_ms,
        }

    @staticmethod
    def _parse_modes(modes: list[str] | None) -> list[PipelineMode]:
        if not modes:
            return [PipelineMode.FULL]
        return [PipelineMode(m) for m in modes]

    @staticmethod
    def _filter_cases(
        cases: list[BenchmarkCaseDefinition],
        request: BenchmarkRequest,
    ) -> list[BenchmarkCaseDefinition]:
        filtered = cases
        if request.categories:
            cats = set(request.categories)
            filtered = [c for c in filtered if c.category in cats]
        if request.case_ids:
            ids = set(request.case_ids)
            filtered = [c for c in filtered if c.id in ids]
        if request.limit:
            filtered = filtered[: request.limit]
        return filtered

    @staticmethod
    def _composite_score(aggregate: dict[str, float]) -> float:
        weights = {
            "retrieval_recall_at_k": 0.2,
            "must_contain_score": 0.2,
            "citation_accuracy": 0.15,
            "abstention_recall": 0.15,
            "stepwise_accuracy": 0.1,
            "mrr": 0.1,
        }
        penalty = aggregate.get("hallucination_rate", 0) * 0.2
        score = sum(aggregate.get(k, 0) * w for k, w in weights.items())
        return max(0.0, min(1.0, score - penalty))

    @staticmethod
    def _rank_cases(
        results: list[dict[str, Any]],
        n: int = 5,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        def score(r: dict[str, Any]) -> float:
            return (
                r.get("retrieval_recall_at_k", 0) * 0.3
                + r.get("must_contain_score", 0) * 0.3
                + r.get("citation_accuracy", 0) * 0.2
                + (1.0 if r.get("abstention_correct") else 0.0 if r.get("should_abstain") else 0.5)
                * 0.2
                - (0.3 if r.get("hallucination") else 0)
            )

        ranked = sorted(results, key=score, reverse=True)
        slim = lambda rows: [  # noqa: E731
            {
                "id": r["id"],
                "query": r["query"],
                "category": r["category"],
                "score": score(r),
                "retrieval_recall_at_k": r.get("retrieval_recall_at_k"),
                "hallucination": r.get("hallucination"),
            }
            for r in rows
        ]
        return slim(ranked[:n]), slim(ranked[-n:][::-1])

    @staticmethod
    def _export_csv(rows: list[dict[str, Any]], path: Path) -> None:
        if not rows:
            return
        fields = [
            "id",
            "category",
            "pipeline_mode",
            "query",
            "should_abstain",
            "abstained",
            "abstention_correct",
            "hallucination",
            "retrieval_recall_at_k",
            "mrr",
            "ndcg_at_k",
            "definition_accuracy",
            "unsupported_claim_ratio",
            "stepwise_accuracy",
            "ordered_step_accuracy",
            "missing_step_rate",
            "extra_step_rate",
            "step_precision",
            "step_recall",
            "citation_accuracy",
            "citation_coverage_per_sentence",
            "definition_retrieved",
            "definition_selected",
            "definition_used",
            "definition_correct",
            "verification_skipped",
            "verification_skip_reason",
            "must_contain_score",
            "must_not_violations",
            "retrieval_confidence",
            "retrieval_ms",
            "rerank_ms",
            "generation_ms",
            "verification_ms",
            "total_ms",
            "answer_preview",
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fields})
