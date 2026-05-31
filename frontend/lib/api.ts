import type {
  AnomalyResponse,
  ChatRequest,
  DocumentInfo,
  EvidenceSufficiency,
  RetrievedSource,
  RetrievalDebug,
  SummarizeResponse,
  UploadResponse,
  VerificationResult,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      typeof body.detail === "string" ? body.detail : "Request failed"
    );
  }
  return res.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: form,
  });

  return handleResponse<UploadResponse>(res);
}

export async function getDocument(documentId: string): Promise<DocumentInfo> {
  const res = await fetch(`${API_BASE}/documents/${documentId}`);
  return handleResponse<DocumentInfo>(res);
}

export async function summarizeDocument(
  documentId: string,
  focus?: string
): Promise<SummarizeResponse> {
  const res = await fetch(`${API_BASE}/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, focus: focus || null }),
  });
  return handleResponse<SummarizeResponse>(res);
}

export async function detectAnomalies(
  documentId: string,
  parameters?: string[]
): Promise<AnomalyResponse> {
  const res = await fetch(`${API_BASE}/anomaly`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document_id: documentId,
      parameters: parameters ?? null,
    }),
  });
  return handleResponse<AnomalyResponse>(res);
}

export interface BenchmarkRunSummary {
  aggregate_score: number;
  retrieval_recall_at_k: number;
  mrr: number;
  ndcg_at_k: number;
  definition_accuracy: number;
  hallucination_rate: number;
  unsupported_claim_ratio: number;
  abstention_precision: number;
  abstention_recall: number;
  stepwise_accuracy: number;
  citation_accuracy: number;
  retrieval_ms: number;
  rerank_ms: number;
  generation_ms: number;
  verification_ms: number;
  total_ms: number;
}

export interface BenchmarkCaseResultRow {
  id: string;
  category: string;
  query: string;
  pipeline_mode?: string;
  should_abstain?: boolean;
  abstained?: boolean;
  hallucination?: boolean;
  retrieval_recall_at_k: number;
  retrieval_confidence?: string;
  must_contain_score?: number;
  total_ms: number;
  answer_preview: string;
}

export interface BenchmarkResponse {
  document_id: string;
  timestamp: string;
  case_count: number;
  modes: string[];
  summary: BenchmarkRunSummary;
  by_category: Record<string, Record<string, number>>;
  mode_comparison: Record<string, Record<string, number>>;
  best_cases: Array<{
    id: string;
    query: string;
    category: string;
    score: number;
  }>;
  worst_cases: Array<{
    id: string;
    query: string;
    category: string;
    score: number;
  }>;
  plot_files: string[];
  results_json: string;
  results_csv: string;
  case_results: BenchmarkCaseResultRow[];
  retrieval_accuracy?: number;
  grounding_score?: number;
}

export interface BenchmarkDataset {
  version: string;
  description: string;
  categories: string[];
  case_count: number;
}

export interface BenchmarkRunOptions {
  limit?: number;
  compare_baselines?: boolean;
  categories?: string[];
  generate_plots?: boolean;
}

export async function getBenchmarkDataset(): Promise<BenchmarkDataset> {
  const res = await fetch(`${API_BASE}/benchmark/dataset`);
  return handleResponse<BenchmarkDataset>(res);
}

export function benchmarkPlotUrl(filename: string): string {
  return `${API_BASE}/benchmark/plots/${filename}`;
}

export async function runBenchmark(
  documentId: string,
  options: BenchmarkRunOptions = {}
): Promise<BenchmarkResponse> {
  const res = await fetch(`${API_BASE}/benchmark/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document_id: documentId,
      limit: options.limit,
      compare_baselines: options.compare_baselines ?? false,
      categories: options.categories,
      generate_plots: options.generate_plots ?? true,
    }),
  });
  return handleResponse<BenchmarkResponse>(res);
}

export function streamChat(
  request: ChatRequest,
  onToken: (token: string) => void,
  onSources: (sources: RetrievedSource[]) => void,
  onDebug: (debug: RetrievalDebug) => void,
  onRevision: (content: string) => void,
  onDone: (payload: {
    sources?: RetrievedSource[];
    verification?: VerificationResult;
    retrieval_debug?: RetrievalDebug;
    final_answer?: string | null;
    evidence_sufficiency?: EvidenceSufficiency;
    retrieval_confidence?: string;
    gated?: boolean;
  }) => void,
  onError: (message: string) => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(
          typeof body.detail === "string" ? body.detail : "Chat failed"
        );
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response stream");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const lines = part.split("\n");
          let event = "message";
          let data = "";

          for (const line of lines) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            if (line.startsWith("data:")) data = line.slice(5).trim();
          }

          if (!data) continue;

          try {
            const parsed = JSON.parse(data) as {
              content?: string;
              message?: string;
              sources?: RetrievedSource[];
              verification?: VerificationResult;
              retrieval_debug?: RetrievalDebug;
              final_answer?: string | null;
              evidence_sufficiency?: EvidenceSufficiency;
              retrieval_confidence?: string;
              gated?: boolean;
            };

            if (event === "sources" && parsed.sources) {
              onSources(parsed.sources);
            } else if (event === "debug") {
              onDebug(parsed as unknown as RetrievalDebug);
            } else if (event === "token" && parsed.content) {
              onToken(parsed.content);
            } else if (event === "revision" && parsed.content) {
              onRevision(parsed.content);
            } else if (event === "done") {
              onDone({
                sources: parsed.sources,
                verification: parsed.verification,
                retrieval_debug: parsed.retrieval_debug,
                final_answer: parsed.final_answer,
                evidence_sufficiency: parsed.evidence_sufficiency,
                retrieval_confidence: parsed.retrieval_confidence,
                gated: parsed.gated,
              });
            } else if (event === "error") {
              onError(parsed.message ?? "Stream error");
            }
          } catch {
            // ignore malformed frames
          }
        }
      }

      onDone({});
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      onError(err instanceof Error ? err.message : "Stream failed");
    }
  })();

  return () => controller.abort();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}
