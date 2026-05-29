"use client";

import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import type {
  EvidenceSufficiency,
  RetrievedSource,
  RetrievalDebug,
  VerificationResult,
} from "@/lib/types";
import { BookOpen, ChevronDown, ShieldAlert, ShieldCheck } from "lucide-react";
import { useState } from "react";

interface RetrievedSourcesProps {
  sources: RetrievedSource[];
  verification?: VerificationResult | null;
  debug?: RetrievalDebug | null;
  retrievalConfidence?: string | null;
  evidenceSufficiency?: EvidenceSufficiency | null;
}

function confidenceVariant(confidence: string): "success" | "warning" | "default" {
  if (confidence === "high") return "success";
  if (confidence === "low") return "warning";
  return "default";
}

export function RetrievedSources({
  sources,
  verification,
  debug,
  retrievalConfidence,
  evidenceSufficiency,
}: RetrievedSourcesProps) {
  const [showDebug, setShowDebug] = useState(false);

  const confidence =
    retrievalConfidence ?? debug?.retrieval_confidence ?? evidenceSufficiency?.confidence;

  if (sources.length === 0 && !verification && !debug && !confidence) return null;

  const riskVariant =
    verification?.hallucination_risk === "high" ||
    verification?.hallucination_risk === "medium"
      ? "warning"
      : "success";

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 space-y-3 rounded-card border border-ghost-border bg-paper-white p-4"
    >
      {confidence && (
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={confidenceVariant(confidence)}>
            retrieval confidence: {confidence}
          </Badge>
          {evidenceSufficiency && !evidenceSufficiency.sufficient && (
            <Badge variant="warning">evidence gated</Badge>
          )}
          {evidenceSufficiency?.authoritative_definitions_found && (
            <Badge variant="success">authoritative defs</Badge>
          )}
          {evidenceSufficiency?.missing_definition_entities &&
            evidenceSufficiency.missing_definition_entities.length > 0 && (
              <Badge variant="warning">
                missing defs:{" "}
                {evidenceSufficiency.missing_definition_entities.join(", ")}
              </Badge>
            )}
        </div>
      )}

      {sources.length > 0 && (
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-electric-violet" />
            <p className="font-display text-heading-sm text-midnight-ink">
              Retrieved Sources ({sources.length})
            </p>
          </div>
          <div className="mt-3 space-y-2">
            {sources.map((src) => (
              <div
                key={src.chunk_id}
                className="rounded-card bg-cloud-canvas p-3 text-caption text-muted-ash"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="accent">Source {src.source_index}</Badge>
                  {(debug?.pinned_chunks?.some((p) => p.chunk_id === src.chunk_id) ||
                    evidenceSufficiency?.pinned_chunk_ids?.includes(src.chunk_id)) && (
                    <Badge variant="success">pinned definition</Badge>
                  )}
                  {src.page_number != null && (
                    <span className="text-midnight-ink">Page {src.page_number}</span>
                  )}
                  <span>vector={src.vector_score.toFixed(3)}</span>
                  <span>rerank={src.rerank_score.toFixed(3)}</span>
                  {src.bm25_score != null && (
                    <span>bm25={src.bm25_score.toFixed(3)}</span>
                  )}
                  {(src.entity_hits ?? 0) > 0 && (
                    <span>entities={src.entity_hits}</span>
                  )}
                </div>
                <p className="mt-2 leading-relaxed">{src.excerpt}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {verification && (
        <div className="border-t border-ghost-border pt-3">
          <div className="flex flex-wrap items-center gap-2">
            {verification.supported ? (
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
            ) : (
              <ShieldAlert className="h-4 w-4 text-amber-600" />
            )}
            <p className="font-display text-heading-sm text-midnight-ink">
              Grounding Check
            </p>
            <Badge variant={verification.supported ? "success" : "warning"}>
              {verification.supported ? "Supported" : "Issues found"}
            </Badge>
            <Badge variant={riskVariant}>
              risk: {verification.hallucination_risk}
            </Badge>
            {verification.rewritten && (
              <Badge variant="accent">Rewritten</Badge>
            )}
            {verification.regenerated && (
              <Badge variant="accent">Regenerated</Badge>
            )}
            {(verification.unsupported_ratio ?? 0) > 0 && (
              <Badge variant="warning">
                {Math.round((verification.unsupported_ratio ?? 0) * 100)}% unsupported
              </Badge>
            )}
          </div>
          {verification.unsupported_claims.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-caption text-muted-ash">
              {verification.unsupported_claims.map((claim, i) => (
                <li key={i}>
                  {claim.claim}
                  {claim.reason ? ` — ${claim.reason}` : ""}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {debug && (
        <div className="border-t border-ghost-border pt-3">
          <button
            type="button"
            onClick={() => setShowDebug(!showDebug)}
            className="flex w-full items-center justify-between text-caption text-midnight-ink"
          >
            <span className="font-display text-heading-sm">Retrieval Debug</span>
            <ChevronDown
              className={`h-4 w-4 transition-transform ${showDebug ? "rotate-180" : ""}`}
            />
          </button>
          {showDebug && (
            <div className="mt-3 space-y-2 text-caption text-muted-ash">
              <p>
                <strong>Original:</strong> {debug.original_query}
              </p>
              {debug.core_query && debug.core_query !== debug.original_query && (
                <p>
                  <strong>Core query:</strong> {debug.core_query}
                </p>
              )}
              <p>
                <strong>Retrieval query:</strong> {debug.retrieval_query}
              </p>
              {debug.entities_detected.length > 0 && (
                <p>
                  <strong>Entities:</strong> {debug.entities_detected.join(", ")}
                </p>
              )}
              {debug.evidence_coverage && (
                <p>
                  <strong>Coverage:</strong>{" "}
                  def={String(debug.evidence_coverage.definition)} beh=
                  {String(debug.evidence_coverage.behavior)} exc=
                  {String(debug.evidence_coverage.exceptions)} int=
                  {String(debug.evidence_coverage.interactions)}
                  {debug.evidence_coverage.missing_categories.length > 0 &&
                    ` missing=[${debug.evidence_coverage.missing_categories.join(", ")}]`}
                </p>
              )}
              {debug.rejected_chunks.length > 0 && (
                <div>
                  <p className="mb-1 font-medium text-midnight-ink">
                    Rejected after rerank ({debug.rejected_chunks.length})
                  </p>
                  {debug.rejected_chunks.slice(0, 3).map((c) => (
                    <p key={c.chunk_id} className="truncate">
                      Source {c.source_index} rerank={c.rerank_score.toFixed(3)} —{" "}
                      {c.excerpt.slice(0, 80)}…
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
