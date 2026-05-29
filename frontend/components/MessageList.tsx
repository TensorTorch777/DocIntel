"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/lib/types";
import { RetrievedSources } from "@/components/RetrievedSources";
import { cn } from "@/lib/utils";
import { User, Bot } from "lucide-react";

interface MessageListProps {
  messages: ChatMessage[];
}

function StreamingCursor() {
  return (
    <span className="ml-0.5 inline-block h-4 w-0.5 animate-blink bg-electric-violet align-middle" />
  );
}

export function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex h-full min-h-[320px] flex-col items-center justify-center text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-card bg-electric-violet/10">
          <Bot className="h-6 w-6 text-electric-violet" />
        </div>
        <p className="mt-4 font-display text-heading-sm text-midnight-ink">
          Ready to analyze
        </p>
        <p className="mt-2 max-w-sm text-caption text-muted-ash">
          Select a task and ask a question. Responses stream in real time from
          your indexed document.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {messages.map((msg) => (
        <motion.div
          key={msg.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            "flex gap-3",
            msg.role === "user" ? "flex-row-reverse" : "flex-row w-full"
          )}
        >
          <div
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-card",
              msg.role === "user"
                ? "bg-midnight-ink"
                : "bg-electric-violet/10"
            )}
          >
            {msg.role === "user" ? (
              <User className="h-4 w-4 text-paper-white" />
            ) : (
              <Bot className="h-4 w-4 text-electric-violet" />
            )}
          </div>

          <div
            className={cn(
              "min-w-0 rounded-card px-4 py-3",
              msg.role === "user"
                ? "max-w-[85%] bg-midnight-ink text-paper-white"
                : "w-full max-w-full border border-ghost-border bg-paper-white"
            )}
          >
            {msg.role === "assistant" ? (
              <>
                <div className="prose-docintel">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                  {msg.streaming && <StreamingCursor />}
                </div>
                {!msg.streaming && (msg.sources?.length || msg.verification || msg.retrievalDebug || msg.retrievalConfidence) && (
                  <RetrievedSources
                    sources={msg.sources ?? []}
                    verification={msg.verification}
                    debug={msg.retrievalDebug}
                    retrievalConfidence={msg.retrievalConfidence}
                    evidenceSufficiency={msg.evidenceSufficiency}
                  />
                )}
              </>
            ) : (
              <p className="text-body">{msg.content}</p>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
