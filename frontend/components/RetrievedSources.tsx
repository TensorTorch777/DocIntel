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
      className="mt-5 space-y-3 rounded-card border border-charcoal bg-charcoal p-4 shadow-inset"
    >
      {confidence && (
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={confidenceVariant(confidence)}>
            Confidence: {confidence}
          </Badge>
          {evidenceSufficiency && !evidenceSufficiency.sufficient && (
            <Badge variant="warning">Evidence gated</Badge>
          )}
        </div>
      )}

      {sources.length > 0 && (
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-iridescent" />
            <p className="font-display text-sm font-medium text-ghost-ash">
              Sources ({sources.length})
            </p>
          </div>
          <div className="mt-3 space-y-2">
            {sources.map((src) => (
              <div
                key={src.chunk_id}
                className="border-b border-charcoal py-2.5 text-caption text-slate last:border-b-0"
              >
                <div className="flex flex-wrap items-center gap-2">
                  {src.page_number != null && (
                    <span className="font-medium text-ghost-ash">
                      Page {src.page_number}
                    </span>
                  )}
                  <span className="text-slate/80">
                    vector {src.vector_score.toFixed(2)} · rerank{" "}
                    {src.rerank_score.toFixed(2)}
                  </span>
                </div>
                <p className="mt-1.5 leading-relaxed">{src.excerpt}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {verification && (
        <div className="divider-subtle pt-3">
          <div className="flex flex-wrap items-center gap-2">
            {verification.supported ? (
              <ShieldCheck className="h-4 w-4 text-ghost-ash" />
            ) : (
              <ShieldAlert className="h-4 w-4 text-accent" />
            )}
            <p className="text-sm font-medium text-ghost-ash">Grounding</p>
            <Badge variant={verification.supported ? "success" : "warning"}>
              {verification.supported ? "Supported" : "Review needed"}
            </Badge>
            <Badge variant={riskVariant}>
              {verification.hallucination_risk} risk
            </Badge>
          </div>
          {verification.unsupported_claims.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-caption text-slate">
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
        <div className="divider-subtle pt-3">
          <button
            type="button"
            onClick={() => setShowDebug(!showDebug)}
            className="flex w-full items-center justify-between text-caption text-ghost-ash"
          >
            <span className="text-sm font-medium">Retrieval internals</span>
            <ChevronDown
              className={`h-4 w-4 text-slate transition-transform ${showDebug ? "rotate-180" : ""}`}
            />
          </button>
          {showDebug && (
            <div className="mt-3 space-y-2 text-caption text-slate">
              <p>
                <strong className="text-ghost-ash">Original:</strong>{" "}
                {debug.original_query}
              </p>
              {debug.core_query && debug.core_query !== debug.original_query && (
                <p>
                  <strong className="text-ghost-ash">Core query:</strong>{" "}
                  {debug.core_query}
                </p>
              )}
              <p>
                <strong className="text-ghost-ash">Retrieval query:</strong>{" "}
                {debug.retrieval_query}
              </p>
              {debug.entities_detected.length > 0 && (
                <p>
                  <strong className="text-ghost-ash">Entities:</strong>{" "}
                  {debug.entities_detected.join(", ")}
                </p>
              )}
              {debug.rejected_chunks.length > 0 && (
                <div>
                  <p className="mb-1 font-medium text-ghost-ash">
                    Rejected after rerank ({debug.rejected_chunks.length})
                  </p>
                  {debug.rejected_chunks.slice(0, 3).map((c) => (
                    <p key={c.chunk_id} className="truncate">
                      p.{c.page_number ?? "?"} · {c.excerpt.slice(0, 80)}…
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
