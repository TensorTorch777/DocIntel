"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Header } from "@/components/Header";
import { UploadZone } from "@/components/UploadZone";
import { DocumentSummary } from "@/components/DocumentSummary";
import { ChatPanel } from "@/components/ChatPanel";
import { useDocuments } from "@/hooks/useDocuments";
import { checkHealth, uploadDocument } from "@/lib/api";
import type { StoredDocument } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import { cn } from "@/lib/utils";

const PAGE_X =
  "px-6 md:px-12 lg:px-16 xl:px-24 2xl:px-32";

const FEATURES = [
  "Hybrid retrieval",
  "Cross-encoder rerank",
  "Evidence gating",
  "Citation grounding",
] as const;

const WORKFLOW = [
  { step: 1, label: "Upload document", active: true },
  { step: 2, label: "Select mode", active: false },
  { step: 3, label: "Ask question", active: false },
  { step: 4, label: "View answer", active: false },
] as const;

function DocIntelWorkspace() {
  const {
    activeDocument,
    addDocument,
    removeDocument,
    clearDocuments,
    setActiveId,
  } = useDocuments();

  const [apiOnline, setApiOnline] = useState(false);
  const [uploading, setUploading] = useState(false);
  const replaceInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    checkHealth().then(setApiOnline);
    const interval = setInterval(() => checkHealth().then(setApiOnline), 15000);
    return () => clearInterval(interval);
  }, []);

  const handleUploaded = useCallback(
    (doc: StoredDocument) => {
      if (activeDocument) {
        removeDocument(activeDocument.document_id);
      }
      addDocument(doc);
      setActiveId(doc.document_id);
      setUploading(false);
    },
    [activeDocument, addDocument, removeDocument, setActiveId]
  );

  const handleReplace = useCallback(() => {
    replaceInputRef.current?.click();
  }, []);

  const handleStartOver = useCallback(() => {
    clearDocuments();
    setUploading(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [clearDocuments]);

  const hasDocument = Boolean(activeDocument);

  if (hasDocument && activeDocument) {
    return (
      <div className="flex min-h-screen flex-col bg-midnight">
        <Header
          apiOnline={apiOnline}
          hasDocument
          onStartOver={handleStartOver}
        />

        <DocumentSummary
          document={activeDocument}
          uploading={uploading}
          onReplace={handleReplace}
        />

        <input
          ref={replaceInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            setUploading(true);
            try {
              const result = await uploadDocument(file);
              handleUploaded({
                document_id: result.document_id,
                filename: result.filename,
                page_count: result.page_count,
                chunk_count: result.chunk_count,
                uploadedAt: new Date().toISOString(),
              });
            } catch {
              setUploading(false);
            }
            e.target.value = "";
          }}
        />

        <main
          id="workspace"
          className={cn("flex min-h-0 flex-1 flex-col py-6", PAGE_X)}
        >
          <div className="flex min-h-0 flex-1 flex-col obsidian-glass">
            <ChatPanel document={activeDocument} />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full bg-midnight">
      <Header apiOnline={apiOnline} />

      <section className="clyde-atmosphere relative w-full min-h-[calc(100vh-3.5rem)]">
        <div
          className={cn(
            "relative z-10 grid w-full min-h-[calc(100vh-3.5rem)] grid-cols-1 items-center gap-12 py-12 lg:grid-cols-2 lg:gap-16 xl:gap-24",
            PAGE_X
          )}
        >
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="flex flex-col justify-center lg:pr-8 xl:pr-12"
          >
            <p className="text-caption text-slate">Document intelligence</p>
            <h1 className="mt-4 font-display text-[clamp(2.75rem,5.5vw,4.5rem)] font-normal leading-[1.02] tracking-[-0.03em] text-ghost-ash">
              Turn technical manuals into answers
            </h1>
            <p className="mt-8 text-subheading font-light leading-relaxed text-slate">
              Upload a PDF, pick Q&amp;A, Summarize, or Anomalies — get grounded
              answers with visible retrieval and citations.
            </p>

            <ul className="mt-10 flex flex-wrap gap-3">
              {FEATURES.map((f) => (
                <li
                  key={f}
                  className="rounded-btn bg-charcoal px-4 py-2 text-caption text-ghost-ash shadow-inset"
                >
                  {f}
                </li>
              ))}
            </ul>

            <div className="mt-10 flex flex-wrap items-center gap-4">
              <Button
                type="button"
                variant="primary"
                className="!text-midnight"
                onClick={() =>
                  document
                    .getElementById("upload")
                    ?.scrollIntoView({ behavior: "smooth" })
                }
              >
                Upload a document
              </Button>
              <Link
                href="/architecture"
                className="text-body text-slate underline underline-offset-4 decoration-charcoal transition-colors hover:text-ghost-ash"
              >
                View architecture
              </Link>
            </div>

            <div className="obsidian-glass mt-12 w-full p-card">
              <p className="text-body leading-relaxed text-slate">
                Domain-aware technical Q&amp;A — hybrid retrieval, cross-encoder
                reranking, and evidence gating built in.
              </p>
            </div>
          </motion.div>

          <motion.div
            id="upload"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.1, ease: "easeOut" }}
            className="flex h-full min-h-[420px] w-full flex-col justify-center lg:min-h-[min(72vh,720px)] lg:pl-4 xl:pl-8"
          >
            <div className="mb-6 flex items-baseline justify-between gap-4">
              <p className="text-caption text-slate">Step 1 · Upload document</p>
              {!apiOnline && (
                <p className="text-caption text-accent">API offline</p>
              )}
            </div>
            <UploadZone
              featured
              onUploaded={(doc) => {
                setUploading(true);
                handleUploaded(doc);
              }}
            />
          </motion.div>
        </div>
      </section>

      <section className={cn("w-full pb-24 pt-4", PAGE_X)}>
        <div className="divider-subtle" />
        <ol className="relative z-10 mt-12 grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
          {WORKFLOW.map((item, i) => (
            <motion.li
              key={item.step}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.05 }}
              className={cn(
                "rounded-card px-5 py-5 transition-colors",
                item.active
                  ? "obsidian-glass ring-1 ring-accent/30"
                  : "bg-charcoal shadow-inset"
              )}
            >
              <span
                className={cn(
                  "font-display text-caption",
                  item.active ? "text-iridescent" : "text-slate"
                )}
              >
                {String(item.step).padStart(2, "0")}
              </span>
              <p
                className={cn(
                  "mt-2 text-body",
                  item.active ? "text-ghost-ash" : "text-slate"
                )}
              >
                {item.label}
              </p>
            </motion.li>
          ))}
        </ol>
      </section>

      <footer
        className={cn(
          "divider-subtle w-full py-8 text-center text-caption text-slate",
          PAGE_X
        )}
      >
        DocIntel
      </footer>
    </div>
  );
}

export function DocIntelApp() {
  return <DocIntelWorkspace />;
}
