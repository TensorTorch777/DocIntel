"use client";

import { Header } from "@/components/Header";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  runBenchmark,
  checkHealth,
  getBenchmarkDataset,
  benchmarkPlotUrl,
  type BenchmarkResponse,
  type BenchmarkDataset,
} from "@/lib/api";
import { useDocuments } from "@/hooks/useDocuments";
import {
  Loader2,
  Play,
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Clock,
  Shield,
  BarChart3,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

function MetricCard({
  label,
  value,
  suffix = "",
  sub,
}: {
  label: string;
  value: number;
  suffix?: string;
  sub?: string;
}) {
  const display =
    suffix === "%"
      ? `${(value * 100).toFixed(1)}%`
      : suffix === "ms"
        ? `${value.toFixed(0)}ms`
        : value.toFixed(3);
  return (
    <div className="rounded-card border border-ghost-border bg-cloud-canvas p-4">
      <p className="text-caption text-muted-ash">{label}</p>
      <p className="mt-1 font-display text-heading font-medium text-midnight-ink">
        {display}
      </p>
      {sub && <p className="mt-1 text-caption text-muted-ash">{sub}</p>}
    </div>
  );
}

function ScoreRing({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80 ? "text-emerald-600" : pct >= 60 ? "text-amber-600" : "text-red-600";
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-ghost-border bg-paper-white p-8">
      <div
        className={`font-display text-[56px] font-medium leading-none tracking-tight ${color}`}
      >
        {pct}%
      </div>
      <p className="mt-2 text-caption text-muted-ash">Aggregate score</p>
    </div>
  );
}

function CategoryBar({
  category,
  metrics,
}: {
  category: string;
  metrics: Record<string, number>;
}) {
  const recall = metrics.retrieval_recall_at_k ?? 0;
  const mustContain = metrics.must_contain_score ?? 0;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-caption">
        <span className="font-medium text-midnight-ink">
          {category.replace(/_/g, " ")}
        </span>
        <span className="text-muted-ash">
          recall {(recall * 100).toFixed(0)}% · content {(mustContain * 100).toFixed(0)}%
        </span>
      </div>
      <div className="flex h-2 overflow-hidden rounded-full bg-ghost-border">
        <div
          className="bg-indigo-500 transition-all"
          style={{ width: `${recall * 100}%` }}
        />
        <div
          className="bg-emerald-400 transition-all"
          style={{ width: `${mustContain * 50}%` }}
        />
      </div>
    </div>
  );
}

function ConfidenceChart({ results }: { results: BenchmarkResponse["case_results"] }) {
  const counts = useMemo(() => {
    const c = { high: 0, medium: 0, low: 0, unknown: 0 };
    for (const r of results) {
      const key = (r.retrieval_confidence ?? "unknown") as keyof typeof c;
      if (key in c) c[key]++;
      else c.unknown++;
    }
    return c;
  }, [results]);
  const total = results.length || 1;
  return (
    <div className="space-y-3">
      {(["high", "medium", "low", "unknown"] as const).map((level) => (
        <div key={level} className="flex items-center gap-3">
          <span className="w-16 text-caption capitalize text-muted-ash">{level}</span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-ghost-border">
            <div
              className={`h-full rounded-full ${
                level === "high"
                  ? "bg-emerald-500"
                  : level === "medium"
                    ? "bg-sky-400"
                    : level === "low"
                      ? "bg-amber-400"
                      : "bg-slate-300"
              }`}
              style={{ width: `${(counts[level] / total) * 100}%` }}
            />
          </div>
          <span className="w-8 text-right text-caption text-muted-ash">
            {counts[level]}
          </span>
        </div>
      ))}
    </div>
  );
}

function LatencyBars({ summary }: { summary: BenchmarkResponse["summary"] }) {
  const stages = [
    { label: "Retrieval", ms: summary.retrieval_ms, color: "bg-indigo-500" },
    { label: "Rerank", ms: summary.rerank_ms, color: "bg-violet-500" },
    { label: "Generation", ms: summary.generation_ms, color: "bg-purple-500" },
    { label: "Verification", ms: summary.verification_ms, color: "bg-fuchsia-400" },
  ];
  const max = Math.max(...stages.map((s) => s.ms), 1);
  return (
    <div className="space-y-3">
      {stages.map((s) => (
        <div key={s.label} className="flex items-center gap-3">
          <span className="w-24 text-caption text-muted-ash">{s.label}</span>
          <div className="h-3 flex-1 overflow-hidden rounded-full bg-ghost-border">
            <div
              className={`h-full rounded-full ${s.color}`}
              style={{ width: `${(s.ms / max) * 100}%` }}
            />
          </div>
          <span className="w-14 text-right text-caption text-midnight-ink">
            {s.ms.toFixed(0)}ms
          </span>
        </div>
      ))}
      <p className="text-caption text-muted-ash">
        Total avg: <strong>{summary.total_ms.toFixed(0)}ms</strong> per query
      </p>
    </div>
  );
}

export default function BenchmarkPage() {
  const { documents, activeId, setActiveId } = useDocuments();
  const [apiOnline, setApiOnline] = useState(false);
  const [dataset, setDataset] = useState<BenchmarkDataset | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BenchmarkResponse | null>(null);
  const [limit, setLimit] = useState(25);
  const [compareBaselines, setCompareBaselines] = useState(false);

  useEffect(() => {
    checkHealth().then(setApiOnline);
    getBenchmarkDataset().then(setDataset).catch(() => null);
  }, []);

  const handleRun = async () => {
    if (!activeId) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const data = await runBenchmark(activeId, {
        limit,
        compare_baselines: compareBaselines,
        generate_plots: true,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Benchmark failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Header apiOnline={apiOnline} />
      <main className="mx-auto max-w-page px-6 py-section lg:px-8">
        <div className="mb-8 flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" className="px-3">
              <ArrowLeft className="h-4 w-4" />
              Workspace
            </Button>
          </Link>
          <div>
            <h1 className="font-display text-heading font-medium text-midnight-ink">
              RAG Benchmark Dashboard
            </h1>
            <p className="mt-1 text-caption text-muted-ash">
              {dataset
                ? `${dataset.case_count} cases · retrieval, grounding, abstention, latency`
                : "Evaluation framework for technical RAG"}
            </p>
          </div>
        </div>

        <Card elevated className="mb-8">
          <div className="flex flex-wrap items-end gap-4">
            <div className="min-w-[240px] flex-1">
              <label className="text-caption text-muted-ash">Document</label>
              <select
                value={activeId ?? ""}
                onChange={(e) => setActiveId(e.target.value || null)}
                className="mt-1 w-full rounded-card border border-ghost-border bg-paper-white px-3 py-2 text-body text-midnight-ink"
                disabled={documents.length === 0}
              >
                {documents.length === 0 && (
                  <option value="">Upload a document first</option>
                )}
                {documents.map((doc) => (
                  <option key={doc.document_id} value={doc.document_id}>
                    {doc.filename} ({doc.chunk_count} chunks)
                  </option>
                ))}
              </select>
            </div>
            <div className="w-28">
              <label className="text-caption text-muted-ash">Case limit</label>
              <input
                type="number"
                min={1}
                max={516}
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="mt-1 w-full rounded-card border border-ghost-border bg-paper-white px-3 py-2 text-body"
              />
            </div>
            <label className="flex items-center gap-2 pb-2 text-caption text-muted-ash">
              <input
                type="checkbox"
                checked={compareBaselines}
                onChange={(e) => setCompareBaselines(e.target.checked)}
                className="rounded"
              />
              Compare all 4 pipeline modes
            </label>
            <Button
              onClick={handleRun}
              disabled={!activeId || running || !apiOnline}
              className="shrink-0"
            >
              {running ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Run benchmark
            </Button>
          </div>
          {error && (
            <p className="mt-4 text-caption text-red-600">{error}</p>
          )}
          {running && (
            <p className="mt-4 text-caption text-muted-ash">
              Running live evaluation — metrics computed from actual retrieval and LLM
              responses…
            </p>
          )}
        </Card>

        {result && (
          <>
            <div className="mb-8 grid gap-6 lg:grid-cols-[240px_1fr]">
              <ScoreRing score={result.summary.aggregate_score} />
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                  label="Recall@k"
                  value={result.summary.retrieval_recall_at_k}
                  suffix="%"
                />
                <MetricCard label="MRR" value={result.summary.mrr} />
                <MetricCard
                  label="Hallucination rate"
                  value={result.summary.hallucination_rate}
                  suffix="%"
                />
                <MetricCard
                  label="Citation accuracy"
                  value={result.summary.citation_accuracy}
                  suffix="%"
                />
                <MetricCard
                  label="Abstention precision"
                  value={result.summary.abstention_precision}
                  suffix="%"
                />
                <MetricCard
                  label="Abstention recall"
                  value={result.summary.abstention_recall}
                  suffix="%"
                />
                <MetricCard
                  label="Definition accuracy"
                  value={result.summary.definition_accuracy}
                  suffix="%"
                />
                <MetricCard
                  label="Avg latency"
                  value={result.summary.total_ms}
                  suffix="ms"
                />
              </div>
            </div>

            <div className="mb-8 grid gap-6 lg:grid-cols-2">
              <Card className="p-6">
                <div className="mb-4 flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-indigo-500" />
                  <h2 className="font-display text-heading-sm text-midnight-ink">
                    Category breakdown
                  </h2>
                </div>
                <div className="space-y-4">
                  {Object.entries(result.by_category).map(([cat, metrics]) => (
                    <CategoryBar key={cat} category={cat} metrics={metrics} />
                  ))}
                </div>
              </Card>

              <Card className="p-6">
                <div className="mb-4 flex items-center gap-2">
                  <Shield className="h-4 w-4 text-emerald-500" />
                  <h2 className="font-display text-heading-sm text-midnight-ink">
                    Retrieval confidence
                  </h2>
                </div>
                <ConfidenceChart results={result.case_results} />
              </Card>

              <Card className="p-6">
                <div className="mb-4 flex items-center gap-2">
                  <Clock className="h-4 w-4 text-violet-500" />
                  <h2 className="font-display text-heading-sm text-midnight-ink">
                    Latency breakdown
                  </h2>
                </div>
                <LatencyBars summary={result.summary} />
              </Card>

              {Object.keys(result.mode_comparison).length > 1 && (
                <Card className="p-6">
                  <h2 className="mb-4 font-display text-heading-sm text-midnight-ink">
                    Pipeline comparison
                  </h2>
                  <div className="space-y-3">
                    {Object.entries(result.mode_comparison).map(([mode, m]) => (
                      <div
                        key={mode}
                        className="rounded-card border border-ghost-border p-3"
                      >
                        <p className="text-caption font-medium text-midnight-ink">
                          {mode}
                        </p>
                        <p className="mt-1 text-caption text-muted-ash">
                          Recall {(m.retrieval_recall_at_k * 100).toFixed(0)}% ·
                          Halluc {(m.hallucination_rate * 100).toFixed(1)}% ·{" "}
                          {m.total_ms?.toFixed(0)}ms
                        </p>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>

            <div className="mb-8 grid gap-6 lg:grid-cols-2">
              <Card className="p-6">
                <div className="mb-4 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-500" />
                  <h2 className="font-display text-heading-sm text-midnight-ink">
                    Best queries
                  </h2>
                </div>
                <ul className="space-y-2">
                  {result.best_cases.map((c) => (
                    <li
                      key={c.id}
                      className="rounded-card bg-cloud-canvas p-3 text-caption"
                    >
                      <Badge variant="success" className="mb-1">
                        {((c.score ?? 0) * 100).toFixed(0)}%
                      </Badge>
                      <p className="text-midnight-ink">{c.query}</p>
                    </li>
                  ))}
                </ul>
              </Card>
              <Card className="p-6">
                <div className="mb-4 flex items-center gap-2">
                  <TrendingDown className="h-4 w-4 text-amber-500" />
                  <h2 className="font-display text-heading-sm text-midnight-ink">
                    Worst queries
                  </h2>
                </div>
                <ul className="space-y-2">
                  {result.worst_cases.map((c) => (
                    <li
                      key={c.id}
                      className="rounded-card bg-cloud-canvas p-3 text-caption"
                    >
                      <Badge variant="warning" className="mb-1">
                        {((c.score ?? 0) * 100).toFixed(0)}%
                      </Badge>
                      <p className="text-midnight-ink">{c.query}</p>
                    </li>
                  ))}
                </ul>
              </Card>
            </div>

            {result.plot_files.length > 0 && (
              <Card className="mb-8 p-6">
                <h2 className="mb-4 font-display text-heading-sm text-midnight-ink">
                  Evaluation plots
                </h2>
                <div className="grid gap-4 sm:grid-cols-2">
                  {result.plot_files.map((file) => (
                    <div
                      key={file}
                      className="overflow-hidden rounded-card border border-ghost-border"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={benchmarkPlotUrl(file)}
                        alt={file}
                        className="w-full bg-white"
                      />
                      <p className="border-t border-ghost-border px-3 py-2 text-caption text-muted-ash">
                        {file.replace(".png", "").replace(/_/g, " ")}
                      </p>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            <div className="space-y-4">
              <h2 className="font-display text-heading-sm text-midnight-ink">
                Case results ({result.case_results.length})
              </h2>
              {result.case_results.map((row) => (
                <Card key={`${row.id}-${row.pipeline_mode}`} className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <Badge variant="default" className="mb-1">
                        {row.category}
                      </Badge>
                      <p className="font-display text-heading-sm text-midnight-ink">
                        {row.query}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge
                        variant={
                          row.retrieval_recall_at_k >= 0.5 ? "success" : "warning"
                        }
                      >
                        recall {(row.retrieval_recall_at_k * 100).toFixed(0)}%
                      </Badge>
                      {row.hallucination && (
                        <Badge variant="warning">hallucination</Badge>
                      )}
                      {row.abstained && (
                        <Badge variant="default">abstained</Badge>
                      )}
                      <Badge variant="default">
                        {row.retrieval_confidence} conf
                      </Badge>
                      <Badge variant="default">
                        {row.total_ms.toFixed(0)}ms
                      </Badge>
                    </div>
                  </div>
                  <p className="mt-2 rounded-card bg-cloud-canvas p-3 text-caption leading-relaxed text-midnight-ink">
                    {row.answer_preview}
                    {(row.answer_preview?.length ?? 0) >= 400 ? "…" : ""}
                  </p>
                </Card>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
