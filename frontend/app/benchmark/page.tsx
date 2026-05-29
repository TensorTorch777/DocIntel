"use client";

import { Header } from "@/components/Header";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { runBenchmark, checkHealth, type BenchmarkResponse } from "@/lib/api";
import { useDocuments } from "@/hooks/useDocuments";
import { Loader2, Play, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

function MetricCard({
  label,
  value,
  suffix = "",
}: {
  label: string;
  value: number;
  suffix?: string;
}) {
  const pct = suffix === "%" ? (value * 100).toFixed(0) : value.toFixed(2);
  return (
    <div className="rounded-card border border-ghost-border bg-cloud-canvas p-4">
      <p className="text-caption text-muted-ash">{label}</p>
      <p className="mt-1 font-display text-heading font-medium text-midnight-ink">
        {pct}
        {suffix}
      </p>
    </div>
  );
}

export default function BenchmarkPage() {
  const { documents, activeId, setActiveId } = useDocuments();
  const [apiOnline, setApiOnline] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BenchmarkResponse | null>(null);

  useEffect(() => {
    checkHealth().then(setApiOnline);
  }, []);

  const handleRun = async () => {
    if (!activeId) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const data = await runBenchmark(activeId);
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
              RAG Benchmark
            </h1>
            <p className="mt-1 text-caption text-muted-ash">
              Repeatable retrieval and grounding evaluation
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
        </Card>

        {result && (
          <>
            <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                label="Retrieval accuracy"
                value={result.retrieval_accuracy}
                suffix="%"
              />
              <MetricCard
                label="Grounding score"
                value={result.grounding_score}
                suffix="%"
              />
              <MetricCard
                label="Format compliance"
                value={result.format_compliance}
                suffix="%"
              />
              <MetricCard label="Avg citations" value={result.avg_citations} />
            </div>

            <div className="space-y-4">
              {result.results.map((row, i) => (
                <Card key={i} className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <p className="font-display text-heading-sm text-midnight-ink">
                      {row.query}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant={row.retrieval_hit ? "success" : "warning"}>
                        retrieval {row.retrieval_hit ? "hit" : "miss"}
                      </Badge>
                      <Badge
                        variant={row.grounding_supported ? "success" : "warning"}
                      >
                        grounding {row.grounding_supported ? "ok" : "fail"}
                      </Badge>
                      {row.format_compliant === false && (
                        <Badge variant="warning">format fail</Badge>
                      )}
                      <Badge variant="default">
                        risk: {row.hallucination_risk}
                      </Badge>
                    </div>
                  </div>
                  <p className="mt-2 text-caption text-muted-ash">
                    <strong>Retrieval query:</strong> {row.retrieval_query}
                  </p>
                  {row.matched_terms.length > 0 && (
                    <p className="mt-1 text-caption text-muted-ash">
                      <strong>Matched terms:</strong>{" "}
                      {row.matched_terms.join(", ")}
                    </p>
                  )}
                  <p className="mt-2 text-caption text-muted-ash">
                    Citations: {row.citation_count}
                  </p>
                  <p className="mt-2 rounded-card bg-cloud-canvas p-3 text-caption leading-relaxed text-midnight-ink">
                    {row.answer_preview}
                    {row.answer_preview.length >= 400 ? "…" : ""}
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
