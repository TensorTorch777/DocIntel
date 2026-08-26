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
  analyzeMedia,
} from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { useUI } from "@/context/UIContext";
import type { PipelineStageEvent } from "@/lib/types";
import {
  ChevronDown,
  ImagePlus,
  Loader2,
  Mic,
  Paperclip,
  Send,
  Square,
  X,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface ChatAttachment {
  file: File;
  filename: string;
  modality: string;
  previewUrl?: string;
}

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
  const [attachment, setAttachment] = useState<ChatAttachment | null>(null);
  const [recording, setRecording] = useState(false);
  const [mediaBusy, setMediaBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const attachInputRef = useRef<HTMLInputElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
  }, []);

  const pickRecorderMime = () => {
    const types = ["audio/webm", "audio/mp4", "audio/ogg"];
    return types.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
  };

  const attachFile = useCallback((file: File, modalityHint?: string) => {
    const type = file.type || "";
    const modality =
      modalityHint ||
      (type.startsWith("video/")
        ? "video"
        : type.startsWith("audio/")
          ? "audio"
          : "image");
    setAttachment({
      file,
      filename: file.name,
      modality,
      previewUrl: type.startsWith("image/") ? URL.createObjectURL(file) : undefined,
    });
  }, []);

  const startRecording = useCallback(async () => {
    if (recording || mediaBusy) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = pickRecorderMime();
      const recorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blobType = recorder.mimeType || mime || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: blobType });
        const ext = blobType.includes("mp4") ? "m4a" : blobType.includes("ogg") ? "ogg" : "webm";
        const file = new File([blob], `voice-note.${ext}`, { type: blobType });
        attachFile(file, "audio");
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Microphone permission is required to record a voice note.",
        },
      ]);
    }
  }, [attachFile, mediaBusy, recording]);

  const stopRecording = useCallback(() => {
    recorderRef.current?.stop();
    recorderRef.current = null;
    setRecording(false);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!document || loading || mediaBusy) return;
    if (!query.trim() && !attachment) return;

    let attachmentContext: string | null = null;
    let attachmentModality: string | null = attachment?.modality ?? null;
    let displayQuery = query.trim();

    if (attachment) {
      setMediaBusy(true);
      try {
        const analyzed = await analyzeMedia(attachment.file);
        attachmentContext = analyzed.text;
        attachmentModality = analyzed.modality;
        if (!displayQuery && analyzed.transcript_available) {
          const transcript = analyzed.text.split("Transcript:").pop()?.trim() ?? "";
          displayQuery = transcript || `Voice note: ${attachment.filename}`;
        }
        if (!displayQuery) {
          displayQuery = `What does this ${analyzed.modality} show in the indexed document?`;
        }
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: err instanceof Error ? err.message : "Could not read the attachment",
            task,
          },
        ]);
        setMediaBusy(false);
        return;
      }
      setMediaBusy(false);
    }

    const pending = attachment;
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: displayQuery,
      task,
      attachment: pending
        ? { filename: pending.filename, modality: attachmentModality ?? pending.modality }
        : undefined,
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuery("");
    setAttachment(null);
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
        attachment_context: attachmentContext,
        attachment_modality: attachmentModality,
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
      ({ sources, verification, retrieval_debug, final_answer, evidence_sufficiency, retrieval_confidence, pipeline, moe }) => {
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
                  moe: moe ?? null,
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
  }, [document, query, loading, task, scrollToBottom, debugRetrieval, portfolioMode, attachment, mediaBusy]);

  const placeholder =
    task === "qa"
      ? "Ask a question, or attach a screenshot, clip, or voice note…"
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
        <div className="mx-auto max-w-chat space-y-3">
          {attachment && (
            <div className="flex items-center gap-3 rounded-card border border-charcoal bg-charcoal px-3 py-2">
              {attachment.previewUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={attachment.previewUrl}
                  alt=""
                  className="h-10 w-10 rounded object-cover"
                />
              ) : (
                <Paperclip className="h-4 w-4 text-slate" />
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-caption text-ghost-ash">{attachment.filename}</p>
                <p className="text-[11px] text-slate">{attachment.modality}</p>
              </div>
              <button
                type="button"
                onClick={() => setAttachment(null)}
                className="text-slate hover:text-ghost-ash"
                aria-label="Remove attachment"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          <div className="flex gap-2">
            <input
              ref={attachInputRef}
              type="file"
              accept="image/*,video/*,audio/*"
              capture={undefined}
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) attachFile(file);
                e.target.value = "";
              }}
            />
            <Button
              variant="ghost"
              onClick={() => attachInputRef.current?.click()}
              disabled={!document || loading || mediaBusy}
              className="shrink-0"
              aria-label="Attach image, video, or audio"
            >
              <ImagePlus className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              onClick={recording ? stopRecording : startRecording}
              disabled={!document || loading || mediaBusy}
              className={cn("shrink-0", recording && "text-accent")}
              aria-label={recording ? "Stop recording" : "Record voice note"}
            >
              {recording ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </Button>
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
              disabled={!document || loading || mediaBusy || (!query.trim() && !attachment)}
              className="shrink-0 !text-midnight"
              aria-label={task === "qa" ? "Ask" : task === "summarize" ? "Summarize" : "Scan"}
            >
              {loading || mediaBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {task === "qa" ? "Ask" : task === "summarize" ? "Summarize" : "Scan"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
