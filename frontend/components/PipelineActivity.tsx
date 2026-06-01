"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  Check,
  ChevronDown,
  Circle,
  Loader2,
  Minus,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import type { PipelineStageEvent, PipelineStageStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STAGE_ORDER = [
  "understanding_query",
  "query_expansion",
  "definition_resolution",
  "vector_retrieval",
  "bm25_retrieval",
  "rrf_fusion",
  "cross_encoder_reranking",
  "evidence_sufficiency",
  "answer_generation",
  "verification",
] as const;

function stageDetail(
  stage: PipelineStageEvent,
  presentationMode: boolean
): string | null {
  const d = stage.detail ?? {};
  switch (stage.stage) {
    case "understanding_query":
      return d.intent ? `Intent: ${String(d.intent)}` : null;
    case "query_expansion": {
      const terms = d.expanded_terms as string[] | undefined;
      if (!terms?.length) return null;
      if (presentationMode) return `${terms.length} terms added`;
      return terms.slice(0, 6).join(", ") + (terms.length > 6 ? "…" : "");
    }
    case "vector_retrieval":
    case "bm25_retrieval":
      return d.chunk_count != null ? `${d.chunk_count} chunks` : null;
    case "rrf_fusion":
      return d.merged_count != null ? `${d.merged_count} merged` : null;
    case "cross_encoder_reranking": {
      const scores = d.top_scores as { score: number; page: number }[] | undefined;
      if (!scores?.length) return presentationMode ? "Reranked" : null;
      if (presentationMode) return `Top score ${scores[0].score.toFixed(2)}`;
      return scores
        .map((s) => `${s.score.toFixed(2)} (p.${s.page})`)
        .join(" · ");
    }
    case "definition_resolution":
      if (stage.status === "skipped") return "No pins needed";
      return d.pinned_count != null
        ? `${d.pinned_count} definition${d.pinned_count === 1 ? "" : "s"} pinned`
        : null;
    case "evidence_sufficiency":
      return d.confidence
        ? `Confidence: ${d.confidence}${d.gated ? " · gated" : ""}`
        : null;
    case "answer_generation":
      if (stage.status === "skipped") return (d.reason as string) ?? "Skipped";
      if (d.refutation) return "Direct refutation answer";
      return d.mode ? `Mode: ${String(d.mode).replace(/_/g, " ")}` : null;
    case "verification":
      if (d.executed) return "Executed";
      if (d.skipped) {
        const reason = d.skip_reason as string | undefined;
        return reason ? `Skipped (${reason.replace(/_/g, " ")})` : "Skipped";
      }
      return null;
    default:
      return null;
  }
}

function StatusIcon({ status }: { status: PipelineStageStatus }) {
  if (status === "running") {
    return <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" />;
  }
  if (status === "completed") {
    return <Check className="h-3.5 w-3.5 text-ghost-ash" />;
  }
  if (status === "skipped") {
    return <Minus className="h-3.5 w-3.5 text-slate" />;
  }
  return <Circle className="h-2.5 w-2.5 text-charcoal" />;
}

interface PipelineActivityProps {
  stages: PipelineStageEvent[];
  active?: boolean;
  presentationMode?: boolean;
  defaultOpen?: boolean;
}

export function PipelineActivity({
  stages,
  active = false,
  presentationMode = false,
  defaultOpen = true,
}: PipelineActivityProps) {
  const [open, setOpen] = useState(defaultOpen);

  const byStage = new Map(stages.map((s) => [s.stage, s]));
  const ordered: PipelineStageEvent[] = STAGE_ORDER.map((id) => {
    const existing = byStage.get(id);
    if (existing) return existing;
    return {
      stage: id,
      label: id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      status: "pending" as PipelineStageStatus,
      detail: {},
    };
  });

  const completedCount = ordered.filter(
    (s) => s.status === "completed" || s.status === "skipped"
  ).length;

  return (
    <div className="mb-4 overflow-hidden obsidian-glass">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-opacity hover:opacity-80"
      >
        <div className="flex min-w-0 items-center gap-2">
          <Sparkles
            className={cn(
              "h-4 w-4 shrink-0",
              active ? "text-accent" : "text-slate"
            )}
          />
          <span className="font-display text-caption font-medium uppercase tracking-wide text-ghost-ash">
            Pipeline activity
          </span>
          {active && (
            <span className="inline-flex items-center gap-1 rounded-btn border border-accent/50 px-2 py-0.5 text-[11px] text-iridescent">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
              Live
            </span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-[11px] text-slate">
            {completedCount}/{ordered.length}
          </span>
          <ChevronDown
            className={cn(
              "h-4 w-4 text-slate transition-transform",
              open && "rotate-180"
            )}
          />
        </div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div
              className={cn(
                "border-t border-charcoal px-4 py-3",
                presentationMode ? "space-y-0" : "space-y-1"
              )}
            >
              {ordered.map((stage, i) => {
                const detail = stageDetail(stage, presentationMode);
                const isRunning = stage.status === "running";
                return (
                  <motion.div
                    key={stage.stage}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.02 }}
                    className={cn(
                      "relative flex gap-3 py-2",
                      presentationMode && "py-2.5"
                    )}
                  >
                    {i < ordered.length - 1 && (
                      <span
                        className={cn(
                          "absolute left-[7px] top-7 h-[calc(100%-4px)] w-px",
                          stage.status === "completed" || stage.status === "skipped"
                            ? "bg-accent/40"
                            : "bg-charcoal"
                        )}
                      />
                    )}
                    <div className="relative z-10 mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">
                      <StatusIcon status={stage.status} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                        <span
                          className={cn(
                            "text-caption font-medium",
                            stage.status === "pending"
                              ? "text-slate"
                              : "text-ghost-ash",
                            isRunning && "text-iridescent"
                          )}
                        >
                          {stage.label}
                        </span>
                        {isRunning && (
                          <span className="text-[11px] text-iridescent/80">
                            running…
                          </span>
                        )}
                      </div>
                      {detail && stage.status !== "pending" && (
                        <p
                          className={cn(
                            "mt-0.5 text-[11px] leading-snug text-slate",
                            presentationMode && "truncate"
                          )}
                        >
                          {detail}
                        </p>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
