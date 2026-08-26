import type {
  AnomalyResponse,
  ChatRequest,
  DocumentInfo,
  EvidenceSufficiency,
  MediaAnalyzeResponse,
  MoEDecision,
  PipelineStageEvent,
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

export async function analyzeMedia(file: File): Promise<MediaAnalyzeResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/media/analyze`, {
    method: "POST",
    body: form,
  });

  return handleResponse<MediaAnalyzeResponse>(res);
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

export function streamChat(
  request: ChatRequest,
  onToken: (token: string) => void,
  onSources: (sources: RetrievedSource[]) => void,
  onDebug: (debug: RetrievalDebug) => void,
  onRevision: (content: string) => void,
  onPipeline: (stage: PipelineStageEvent) => void,
  onDone: (payload: {
    sources?: RetrievedSource[];
    verification?: VerificationResult;
    retrieval_debug?: RetrievalDebug;
    final_answer?: string | null;
    evidence_sufficiency?: EvidenceSufficiency;
    retrieval_confidence?: string;
    gated?: boolean;
    pipeline?: PipelineStageEvent[];
    moe?: MoEDecision | null;
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
              pipeline?: PipelineStageEvent[];
              moe?: MoEDecision | null;
              stage?: string;
              label?: string;
              status?: PipelineStageEvent["status"];
              detail?: Record<string, unknown>;
            };

            if (event === "sources" && parsed.sources) {
              onSources(parsed.sources);
            } else if (event === "debug") {
              onDebug(parsed as unknown as RetrievalDebug);
            } else if (event === "pipeline" && parsed.stage) {
              onPipeline(parsed as PipelineStageEvent);
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
                pipeline: parsed.pipeline,
                moe: parsed.moe ?? null,
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
