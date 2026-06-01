export type ChatTask = "qa" | "summarize" | "anomaly";

export interface UploadResponse {
  document_id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  message: string;
}

export interface DocumentInfo {
  document_id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
}

export interface StoredDocument extends DocumentInfo {
  uploadedAt: string;
}

export interface RetrievedSource {
  source_index: number;
  chunk_id: string;
  page_number: number | null;
  vector_score: number;
  rerank_score: number;
  bm25_score?: number | null;
  rrf_score?: number | null;
  entity_hits?: number;
  excerpt: string;
  selected?: boolean;
}

export interface RetrievalDebug {
  original_query: string;
  core_query?: string;
  retrieval_query: string;
  entities_detected: string[];
  retrieval_confidence?: string;
  evidence_coverage?: EvidenceCoverage;
  pinned_chunks?: RetrievedSource[];
  vector_candidates: RetrievedSource[];
  bm25_candidates: RetrievedSource[];
  merged_candidates: RetrievedSource[];
  selected_chunks: RetrievedSource[];
  rejected_chunks: RetrievedSource[];
}

export interface UnsupportedClaim {
  claim: string;
  reason?: string | null;
  evidence?: string | null;
}

export interface VerificationResult {
  supported: boolean;
  unsupported_claims: UnsupportedClaim[];
  hallucination_risk: string;
  notes: string;
  rewritten?: boolean;
  regenerated?: boolean;
  total_claims?: number;
  unsupported_ratio?: number;
}

export interface EvidenceCoverage {
  definition: number;
  behavior: number;
  exceptions: number;
  interactions: number;
  query_relevance?: number;
  total_weighted?: number;
  missing_categories: string[];
}

export interface EvidenceSufficiency {
  sufficient: boolean;
  confidence: string;
  coverage_score?: number;
  coverage: EvidenceCoverage;
  message?: string | null;
  entity_mentions?: number;
  definitional_hits?: number;
  top_rerank_score?: number;
  authoritative_definitions_found?: boolean;
  missing_definition_entities?: string[];
  pinned_chunk_ids?: string[];
}

export interface ChatRequest {
  document_id: string;
  query: string;
  task: ChatTask;
  top_k?: number;
  debug?: boolean;
}

export interface AnomalyFlag {
  parameter: string;
  description: string;
  severity: "low" | "medium" | "high";
  source_excerpt: string;
}

export interface AnomalyResponse {
  document_id: string;
  flags: AnomalyFlag[];
  raw_analysis: string | null;
  sources: RetrievedSource[];
}

export interface SummarizeResponse {
  document_id: string;
  summary: string;
  sections: string[];
  sources: RetrievedSource[];
}

export type PipelineStageStatus = "pending" | "running" | "completed" | "skipped";

export interface PipelineStageEvent {
  stage: string;
  label: string;
  status: PipelineStageStatus;
  detail?: Record<string, unknown>;
}

export interface MessagePipelineState {
  stages: PipelineStageEvent[];
  active: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  task?: ChatTask;
  streaming?: boolean;
  sources?: RetrievedSource[];
  verification?: VerificationResult | null;
  retrievalDebug?: RetrievalDebug | null;
  retrievalConfidence?: string | null;
  evidenceSufficiency?: EvidenceSufficiency | null;
  revised?: boolean;
  pipeline?: MessagePipelineState;
}
