"""Generate matplotlib plots from benchmark results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def plot_category_accuracy(
    by_category: dict[str, dict[str, float]],
    output_dir: Path,
) -> Path:
    categories = sorted(by_category.keys())
    scores = [
        by_category[c].get("must_contain_score", by_category[c].get("retrieval_recall_at_k", 0))
        for c in categories
    ]
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = plt.cm.viridis(np.linspace(0.2, 0.85, len(categories)))
    bars = ax.bar(categories, scores, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Accuracy score")
    ax.set_title("Category accuracy (must-contain / retrieval)")
    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, rotation=25, ha="right")
    ax.axhline(y=0.8, color="#94a3b8", linestyle="--", linewidth=1, label="80% target")
    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{score:.0%}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.legend(loc="lower right")
    fig.tight_layout()
    out = output_dir / "category_accuracy.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_hallucination_reduction(
    mode_aggregates: dict[str, dict[str, float]],
    output_dir: Path,
) -> Path:
    modes = list(mode_aggregates.keys())
    rates = [mode_aggregates[m].get("hallucination_rate", 0) for m in modes]
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#ef4444", "#f97316", "#eab308", "#22c55e"][: len(modes)]
    bars = ax.bar(modes, rates, color=colors, edgecolor="white")
    ax.set_ylim(0, max(0.15, max(rates) * 1.2 + 0.02))
    ax.set_ylabel("Hallucination rate")
    ax.set_title("Hallucination rate by pipeline mode")
    ax.set_xticks(range(len(modes)))
    ax.set_xticklabels(modes, rotation=15, ha="right")
    for bar, rate in zip(bars, rates):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.005,
            f"{rate:.1%}",
            ha="center",
            fontsize=9,
        )
    fig.tight_layout()
    out = output_dir / "hallucination_reduction.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_latency_breakdown(
    aggregate: dict[str, float],
    output_dir: Path,
) -> Path:
    stages = ["retrieval_ms", "rerank_ms", "generation_ms", "verification_ms"]
    labels = ["Retrieval", "Rerank", "Generation", "Verification"]
    values = [aggregate.get(s, 0) for s in stages]
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#6366f1", "#8b5cf6", "#a855f7", "#c084fc"]
    bars = ax.bar(labels, values, color=colors, edgecolor="white")
    ax.set_ylabel("Milliseconds (avg)")
    ax.set_title("Latency breakdown per query")
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.02,
            f"{val:.0f}ms",
            ha="center",
            fontsize=9,
        )
    fig.tight_layout()
    out = output_dir / "latency_breakdown.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_recall_at_k(
    case_results: list[dict[str, Any]],
    output_dir: Path,
    k: int = 5,
) -> Path:
    recalls = [r.get("retrieval_recall_at_k", 0) for r in case_results]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(recalls, bins=20, color="#6366f1", edgecolor="white", alpha=0.85)
    ax.axvline(np.mean(recalls) if recalls else 0, color="#ef4444", linestyle="--", label="Mean")
    ax.set_xlabel(f"Recall@{k}")
    ax.set_ylabel("Case count")
    ax.set_title(f"Retrieval recall@{k} distribution")
    ax.legend()
    fig.tight_layout()
    out = output_dir / "retrieval_recall_at_k.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_abstention_accuracy(
    aggregate: dict[str, float],
    output_dir: Path,
) -> Path:
    metrics = ["abstention_precision", "abstention_recall"]
    labels = ["Precision", "Recall"]
    values = [aggregate.get(m, 0) for m in metrics]
    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(labels, values, color=["#0ea5e9", "#06b6d4"], edgecolor="white")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("Abstention accuracy")
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{val:.0%}",
            ha="center",
            fontsize=10,
        )
    fig.tight_layout()
    out = output_dir / "abstention_accuracy.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_pipeline_comparison(
    mode_aggregates: dict[str, dict[str, float]],
    output_dir: Path,
) -> Path:
    modes = list(mode_aggregates.keys())
    metric_keys = [
        ("retrieval_recall_at_k", "Recall@k"),
        ("mrr", "MRR"),
        ("hallucination_rate", "Hallucination"),
        ("citation_accuracy", "Citations"),
    ]
    x = np.arange(len(modes))
    width = 0.18
    fig, ax = plt.subplots(figsize=(11, 6))
    for i, (key, label) in enumerate(metric_keys):
        vals = [mode_aggregates[m].get(key, 0) for m in modes]
        offset = (i - 1.5) * width
        ax.bar(x + offset, vals, width, label=label, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(modes, rotation=12, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("Pipeline mode comparison")
    ax.legend(loc="upper right", ncol=2)
    fig.tight_layout()
    out = output_dir / "pipeline_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_confidence_distribution(
    case_results: list[dict[str, Any]],
    output_dir: Path,
) -> Path:
    conf_map = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
    values = [conf_map.get(r.get("retrieval_confidence", "unknown"), 0) for r in case_results]
    labels = ["unknown", "low", "medium", "high"]
    counts = [values.count(i) for i in range(4)]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(labels, counts, color=["#94a3b8", "#fbbf24", "#60a5fa", "#22c55e"], edgecolor="white")
    ax.set_ylabel("Case count")
    ax.set_title("Retrieval confidence distribution")
    fig.tight_layout()
    out = output_dir / "confidence_distribution.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def generate_all_plots(results: dict[str, Any], plots_dir: Path | str) -> list[str]:
    """Generate all benchmark plots; return relative plot filenames."""
    plots_dir = _ensure_dir(Path(plots_dir))
    generated: list[str] = []

    case_results = results.get("case_results", [])
    aggregate = results.get("aggregate", {})
    by_category = results.get("by_category", {})
    mode_comparison = results.get("mode_comparison", {})

    if by_category:
        p = plot_category_accuracy(by_category, plots_dir)
        generated.append(p.name)

    if mode_comparison:
        p = plot_hallucination_reduction(mode_comparison, plots_dir)
        generated.append(p.name)
        p = plot_pipeline_comparison(mode_comparison, plots_dir)
        generated.append(p.name)
    elif aggregate:
        mode_comparison = {"full": aggregate}
        p = plot_hallucination_reduction(mode_comparison, plots_dir)
        generated.append(p.name)

    if aggregate:
        p = plot_latency_breakdown(aggregate, plots_dir)
        generated.append(p.name)
        p = plot_abstention_accuracy(aggregate, plots_dir)
        generated.append(p.name)

    if case_results:
        p = plot_recall_at_k(case_results, plots_dir)
        generated.append(p.name)
        p = plot_confidence_distribution(case_results, plots_dir)
        generated.append(p.name)

    manifest = plots_dir / "manifest.json"
    manifest.write_text(json.dumps(generated, indent=2), encoding="utf-8")
    return generated


def load_and_plot(results_path: Path, plots_dir: Path | None = None) -> list[str]:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    plots_dir = plots_dir or results_path.parent / "plots"
    return generate_all_plots(results, plots_dir)
