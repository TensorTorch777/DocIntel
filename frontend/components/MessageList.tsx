"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/lib/types";
import { RetrievedSources } from "@/components/RetrievedSources";
import { PipelineActivity } from "@/components/PipelineActivity";
import { cn } from "@/lib/utils";

interface MessageListProps {
  messages: ChatMessage[];
  presentationMode?: boolean;
}

function StreamingCursor() {
  return (
    <span className="ml-0.5 inline-block h-4 w-0.5 animate-blink bg-accent align-middle" />
  );
}

export function MessageList({ messages, presentationMode = false }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center px-4 text-center">
        <p className="font-display text-heading-sm font-normal text-ghost-ash">
          Ask your first question
        </p>
        <p className="mt-3 max-w-md text-caption text-slate">
          Choose Q&amp;A, Summarize, or Anomalies — type, record a voice note,
          or attach a screenshot.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {messages.map((msg) => (
        <motion.div
          key={msg.id}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(msg.role === "user" ? "flex justify-end" : "w-full")}
        >
          {msg.role === "user" ? (
            <div className="max-w-[85%] rounded-card bg-charcoal px-4 py-3 text-body text-ghost-ash shadow-inset">
              {msg.attachment && (
                <p className="mb-2 text-[11px] uppercase tracking-wide text-slate">
                  Attached {msg.attachment.modality}: {msg.attachment.filename}
                </p>
              )}
              {msg.content}
            </div>
          ) : (
            <div className="w-full">
              {msg.pipeline && msg.pipeline.stages.length > 0 && (
                <PipelineActivity
                  stages={msg.pipeline.stages}
                  active={Boolean(msg.streaming && msg.pipeline.active)}
                  presentationMode={presentationMode}
                  defaultOpen={presentationMode || Boolean(msg.streaming)}
                />
              )}
              <div className="prose-docintel">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
                {msg.streaming && <StreamingCursor />}
              </div>
              {!msg.streaming &&
                !presentationMode &&
                (msg.sources?.length ||
                  msg.verification ||
                  msg.retrievalDebug ||
                  msg.retrievalConfidence) && (
                  <RetrievedSources
                    sources={msg.sources ?? []}
                    verification={msg.verification}
                    debug={msg.retrievalDebug}
                    retrievalConfidence={msg.retrievalConfidence}
                    evidenceSufficiency={msg.evidenceSufficiency}
                  />
                )}
              {!msg.streaming &&
                presentationMode &&
                msg.sources &&
                msg.sources.length > 0 && (
                  <p className="mt-3 text-caption text-slate">
                    {msg.sources.length} source
                    {msg.sources.length === 1 ? "" : "s"} cited
                  </p>
                )}
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}
