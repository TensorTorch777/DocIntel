"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Card } from "@/components/ui/Card";
import { cn, formatNumber } from "@/lib/utils";
import type { StoredDocument } from "@/lib/types";
import { FileText, Loader2, Trash2, Upload } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { uploadDocument } from "@/lib/api";

interface UploadPanelProps {
  documents: StoredDocument[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onUploaded: (doc: StoredDocument) => void;
  onRemove: (id: string) => void;
}

export function UploadPanel({
  documents,
  activeId,
  onSelect,
  onUploaded,
  onRemove,
}: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError("Only PDF files are supported");
        return;
      }

      setError(null);
      setUploading(true);
      setProgress(10);

      const interval = setInterval(() => {
        setProgress((p) => Math.min(p + 8, 90));
      }, 400);

      try {
        const result = await uploadDocument(file);
        clearInterval(interval);
        setProgress(100);

        onUploaded({
          document_id: result.document_id,
          filename: result.filename,
          page_count: result.page_count,
          chunk_count: result.chunk_count,
          uploadedAt: new Date().toISOString(),
        });
      } catch (err) {
        clearInterval(interval);
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setTimeout(() => {
          setUploading(false);
          setProgress(0);
        }, 600);
      }
    },
    [onUploaded]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div className="space-y-element">
      <Card elevated>
        <h2 className="font-display text-heading font-medium tracking-tight text-midnight-ink">
          Ingestion
        </h2>
        <p className="mt-2 text-caption text-muted-ash">
          Upload PDF reports for extraction, chunking, and vector indexing.
        </p>

        <motion.div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          whileHover={{ scale: uploading ? 1 : 1.01 }}
          className={cn(
            "mt-6 cursor-pointer rounded-card border border-dashed p-8 text-center transition-colors",
            dragging
              ? "border-electric-violet bg-electric-violet/5"
              : "border-ghost-border bg-cloud-canvas hover:border-electric-violet/30",
            uploading && "pointer-events-none"
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
              e.target.value = "";
            }}
          />

          {uploading ? (
            <div className="space-y-4">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-electric-violet" />
              <p className="text-body text-muted-ash">Indexing document…</p>
              <div className="mx-auto h-1.5 max-w-xs overflow-hidden rounded-pill bg-ghost-border">
                <motion.div
                  className="h-full bg-electric-violet"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ ease: "easeOut" }}
                />
              </div>
            </div>
          ) : (
            <>
              <Upload className="mx-auto h-8 w-8 text-electric-violet" />
              <p className="mt-4 text-body text-midnight-ink">
                Drop PDF here or click to browse
              </p>
              <p className="mt-1 text-caption text-muted-ash">
                Supports multi-hundred-page engineering reports
              </p>
            </>
          )}
        </motion.div>

        <AnimatePresence>
          {error && (
            <motion.p
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-4 text-caption text-red-600"
            >
              {error}
            </motion.p>
          )}
        </AnimatePresence>
      </Card>

      <Card elevated>
        <h3 className="font-display text-heading-sm font-medium text-midnight-ink">
          Indexed Documents
        </h3>
        <div className="mt-4 space-y-3">
          {documents.length === 0 ? (
            <p className="text-caption text-muted-ash">No documents yet.</p>
          ) : (
            documents.map((doc) => (
              <motion.button
                key={doc.document_id}
                layout
                onClick={() => onSelect(doc.document_id)}
                className={cn(
                  "flex w-full items-start gap-3 rounded-card border p-4 text-left transition-colors",
                  activeId === doc.document_id
                    ? "border-electric-violet/30 bg-electric-violet/5"
                    : "border-ghost-border bg-cloud-canvas hover:bg-paper-white"
                )}
              >
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-electric-violet" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-body text-midnight-ink">{doc.filename}</p>
                  <p className="mt-1 text-caption text-muted-ash">
                    {formatNumber(doc.page_count)} pages ·{" "}
                    {formatNumber(doc.chunk_count)} chunks
                  </p>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(doc.document_id);
                  }}
                  className="rounded-pill p-1.5 text-muted-ash hover:bg-red-50 hover:text-red-600"
                  aria-label="Remove document"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </motion.button>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
