"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MessageList } from "@/components/MessageList";
import { TaskSelector } from "@/components/TaskSelector";
import { DocumentStats } from "@/components/DocumentStats";
import type {
  AnomalyFlag,
  ChatMessage,
  ChatTask,
  StoredDocument,
} from "@/lib/types";
import {
  detectAnomalies,
  streamChat,
  summarizeDocument,
} from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { useUI } from "@/context/UIContext";
import type { PipelineStageEvent } from "@/lib/types";
import { ChevronDown, Loader2, Send } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface ChatPanelProps {
  document: StoredDocument | null;
}

function AnomalyResults({ flags }: { flags: AnomalyFlag[] }) {
  if (flags.length === 0) {
    return (
      <p className="text-body text-slate">No anomalies detected in retrieved context.</p>
    );
  }

  const severityColor = {
    low: "default" as const,
    medium: "warning" as const,
    high: "warning" as const,
  };

  return (
    <div className="space-y-3">
      {flags.map((flag, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          className="rounded-card border border-charcoal bg-charcoal p-4 shadow-inset"
        >
          <div className="flex items-center gap-2">
            <p className="text-body font-medium text-ghost-ash">{flag.parameter}</p>
            <Badge variant={severityColor[flag.severity]}>{flag.severity}</Badge>
          </div>
          <p className="mt-2 text-caption text-slate">{flag.description}</p>
          {flag.source_excerpt && (
            <p className="mt-2 border-l-2 border-charcoal pl-3 text-caption italic text-slate">
              {flag.source_excerpt}
            </p>
          )}
        </motion.div>
      ))}
    </div>
  );
}

export function ChatPanel({ document }: ChatPanelProps) {
  const { portfolioMode } = useUI();
  const [task, setTask] = useState<ChatTask>("qa");
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [debugRetrieval, setDebugRetrieval] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [anomalyFlags, setAnomalyFlags] = useState<AnomalyFlag[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!document || !query.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: query.trim(),
      task,
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuery("");
    setLoading(true);
    setAnomalyFlags([]);
    scrollToBottom();

    if (task === "summarize") {
      try {
        const result = await summarizeDocument(document.document_id, userMsg.content);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: result.summary,
            task,
            sources: result.sources,
          },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: err instanceof Error ? err.message : "Summarization failed",
            task,
          },
        ]);
      } finally {
        setLoading(false);
        scrollToBottom();
      }
      return;
    }

    if (task === "anomaly") {
      try {
        const params = userMsg.content
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        const result = await detectAnomalies(
          document.document_id,
          params.length ? params : undefined
        );
        setAnomalyFlags(result.flags);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content:
              result.raw_analysis ??
              (result.flags.length
                ? `Found ${result.flags.length} potential anomaly(ies).`
                : "No anomalies detected."),
            task,
            sources: result.sources,
          },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: err instanceof Error ? err.message : "Anomaly scan failed",
            task,
          },
        ]);
      } finally {
        setLoading(false);
        scrollToBottom();
      }
      return;
    }

    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        task,
        streaming: true,
        pipeline: { stages: [], active: true },
      },
    ]);

    const effectiveDebug = !portfolioMode && debugRetrieval;

    streamChat(
      {
        document_id: document.document_id,
        query: userMsg.content,
        task: "qa",
        debug: effectiveDebug,
      },
      (token) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + token } : m
          )
        );
        scrollToBottom();
      },
      (sources) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, sources } : m
          )
        );
      },
      (debug) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, retrievalDebug: debug } : m
          )
        );
      },
      (revisedContent) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: revisedContent, revised: true }
              : m
          )
        );
        scrollToBottom();
      },
      (stage: PipelineStageEvent) => {
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== assistantId || !m.pipeline) return m;
            const idx = m.pipeline.stages.findIndex((s) => s.stage === stage.stage);
            const stages =
              idx >= 0
                ? m.pipeline.stages.map((s, i) => (i === idx ? stage : s))
                : [...m.pipeline.stages, stage];
            return {
              ...m,
              pipeline: { stages, active: true },
            };
          })
        );
      },
      ({ sources, verification, retrieval_debug, final_answer, evidence_sufficiency, retrieval_confidence, pipeline }) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  streaming: false,
                  content: final_answer ?? m.content,
                  sources: sources ?? m.sources,
                  verification: verification ?? null,
                  retrievalDebug: retrieval_debug ?? m.retrievalDebug,
                  retrievalConfidence: retrieval_confidence ?? null,
                  evidenceSufficiency: evidence_sufficiency ?? null,
                  revised: m.revised || Boolean(final_answer),
                  pipeline: {
                    stages: pipeline ?? m.pipeline?.stages ?? [],
                    active: false,
                  },
                }
              : m
          )
        );
        setLoading(false);
        scrollToBottom();
      },
      (err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: err, streaming: false }
              : m
          )
        );
        setLoading(false);
      }
    );
  }, [document, query, loading, task, scrollToBottom, debugRetrieval, portfolioMode]);

  const placeholder =
    task === "qa"
      ? "Ask a question about the document…"
      : task === "summarize"
        ? "Optional focus (e.g. paging architecture)…"
        : "Optional parameters, comma-separated…";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <DocumentStats document={document} />

      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-charcoal px-6 py-4 md:px-8">
        <TaskSelector value={task} onChange={setTask} />
        {task === "qa" && (
          <div className="text-right">
            <button
              type="button"
              onClick={() => setAdvancedOpen((v) => !v)}
              className="inline-flex items-center gap-1 text-caption text-slate hover:text-ghost-ash"
            >
              Advanced settings
              <ChevronDown
                className={cn(
                  "h-3 w-3 transition-transform",
                  advancedOpen && "rotate-180"
                )}
              />
            </button>
            {advancedOpen && (
              <label className="mt-2 flex cursor-pointer items-start justify-end gap-2 text-caption text-slate">
                <input
                  type="checkbox"
                  checked={debugRetrieval}
                  onChange={(e) => setDebugRetrieval(e.target.checked)}
                  className="mt-0.5 accent-accent"
                />
                <span>Show retrieval debug</span>
              </label>
            )}
          </div>
        )}
      </div>

      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-y-auto px-6 py-6 md:px-8"
      >
        {!document ? (
          <p className="text-center text-body text-slate">
            Upload a document to begin
          </p>
        ) : (
          <>
            <div className="mx-auto w-full max-w-chat">
              <MessageList messages={messages} presentationMode={portfolioMode} />
            </div>
            <AnimatePresence>
              {anomalyFlags.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mx-auto mt-8 max-w-chat border-t border-charcoal pt-6"
                >
                  <p className="mb-4 text-body font-medium text-ghost-ash">
                    Flagged issues
                  </p>
                  <AnomalyResults flags={anomalyFlags} />
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>

      <div className="border-t border-charcoal px-6 py-4 md:px-8">
        <div className="mx-auto flex max-w-chat gap-3">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSubmit()}
            placeholder={document ? placeholder : "Upload a document first"}
            disabled={!document || loading}
            className="flex-1"
          />
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={!document || loading || !query.trim()}
            className="shrink-0 !text-midnight"
            aria-label={task === "qa" ? "Ask" : task === "summarize" ? "Summarize" : "Scan"}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {task === "qa" ? "Ask" : task === "summarize" ? "Summarize" : "Scan"}
          </Button>
        </div>
      </div>
    </div>
  );
}
