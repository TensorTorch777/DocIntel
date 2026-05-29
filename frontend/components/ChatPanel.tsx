"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Card } from "@/components/ui/Card";
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
import { Loader2, Send } from "lucide-react";
import { useCallback, useRef, useState } from "react";

interface ChatPanelProps {
  document: StoredDocument | null;
}

function AnomalyResults({ flags }: { flags: AnomalyFlag[] }) {
  if (flags.length === 0) {
    return (
      <p className="text-body text-muted-ash">No anomalies detected in retrieved context.</p>
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
          transition={{ delay: i * 0.05 }}
          className="rounded-card border border-ghost-border bg-cloud-canvas p-4"
        >
          <div className="flex items-center gap-2">
            <p className="text-body font-bold text-midnight-ink">{flag.parameter}</p>
            <Badge variant={severityColor[flag.severity]}>{flag.severity}</Badge>
          </div>
          <p className="mt-2 text-caption text-muted-ash">{flag.description}</p>
          {flag.source_excerpt && (
            <p className="mt-2 border-l-2 border-electric-violet/30 pl-3 text-caption italic text-muted-ash">
              {flag.source_excerpt}
            </p>
          )}
        </motion.div>
      ))}
    </div>
  );
}

export function ChatPanel({ document }: ChatPanelProps) {
  const [task, setTask] = useState<ChatTask>("qa");
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [debugRetrieval, setDebugRetrieval] = useState(false);
  const [anomalyFlags, setAnomalyFlags] = useState<AnomalyFlag[]>([]);
  const abortRef = useRef<(() => void) | null>(null);
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
      { id: assistantId, role: "assistant", content: "", task, streaming: true },
    ]);

    abortRef.current = streamChat(
      {
        document_id: document.document_id,
        query: userMsg.content,
        task: "qa",
        debug: debugRetrieval,
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
      ({ sources, verification, retrieval_debug, final_answer, evidence_sufficiency, retrieval_confidence }) => {
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
  }, [document, query, loading, task, scrollToBottom, debugRetrieval]);

  const placeholder =
    task === "qa"
      ? "Ask a question about the document…"
      : task === "summarize"
        ? "Optional focus area (e.g. transformer architecture)…"
        : "Optional parameters to inspect, comma-separated…";

  return (
    <Card elevated className="flex min-h-[640px] flex-col">
      <div className="mb-6">
        <h2 className="font-display text-heading font-medium tracking-tight text-midnight-ink">
          Intelligence Workspace
        </h2>
        <p className="mt-1 text-caption text-muted-ash">
          RAG-powered analysis with live streaming
        </p>
      </div>

      <DocumentStats document={document} />

      <div className="mt-6">
        <TaskSelector value={task} onChange={setTask} />
        {task === "qa" && (
          <label className="mt-3 flex cursor-pointer items-center gap-2 text-caption text-muted-ash">
            <input
              type="checkbox"
              checked={debugRetrieval}
              onChange={(e) => setDebugRetrieval(e.target.checked)}
              className="rounded border-ghost-border text-electric-violet focus:ring-electric-violet"
            />
            Show retrieval debug (rewritten query, scores, rejected chunks)
          </label>
        )}
      </div>

      <div
        ref={scrollRef}
        className="mt-6 max-h-[520px] flex-1 overflow-y-auto overflow-x-hidden rounded-card border border-ghost-border bg-cloud-canvas p-5"
      >
        {!document ? (
          <div className="flex h-full min-h-[280px] items-center justify-center text-caption text-muted-ash">
            Upload a document to begin
          </div>
        ) : (
          <>
            <MessageList messages={messages} />
            <AnimatePresence>
              {anomalyFlags.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-6 border-t border-ghost-border pt-6"
                >
                  <p className="mb-4 font-display text-heading-sm text-midnight-ink">
                    Flagged Issues
                  </p>
                  <AnomalyResults flags={anomalyFlags} />
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>

      <div className="mt-6 flex gap-3">
        <Input
          filled
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSubmit()}
          placeholder={document ? placeholder : "Upload a document first"}
          disabled={!document || loading}
          className="flex-1"
        />
        <Button
          onClick={handleSubmit}
          disabled={!document || loading || !query.trim()}
          className="shrink-0 px-6"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          {task === "qa" ? "Ask" : task === "summarize" ? "Summarize" : "Scan"}
        </Button>
      </div>
    </Card>
  );
}
