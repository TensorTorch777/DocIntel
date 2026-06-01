"use client";

import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { StoredDocument } from "@/lib/types";
import { FileText, Loader2, Upload } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { uploadDocument } from "@/lib/api";

interface UploadZoneProps {
  onUploaded: (doc: StoredDocument) => void;
  compact?: boolean;
  featured?: boolean;
}

export function UploadZone({
  onUploaded,
  compact = false,
  featured = false,
}: UploadZoneProps) {
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
    <div className={cn("w-full", compact ? "max-w-md" : "h-full w-full")}>
      <motion.div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !uploading && inputRef.current?.click()}
        whileHover={featured && !uploading ? { scale: 1.005 } : undefined}
        className={cn(
          "group relative cursor-pointer text-center transition-all duration-300",
          featured
            ? cn(
                "obsidian-glass flex min-h-[min(55vh,480px)] w-full flex-col items-center justify-center px-8 py-12 sm:px-12 sm:py-16 lg:min-h-[min(72vh,680px)] lg:px-16 lg:py-20",
                dragging && "ring-1 ring-accent/50"
              )
            : cn(
                "rounded-card border border-charcoal bg-charcoal shadow-inset",
                compact ? "px-6 py-8" : "px-8 py-14",
                dragging && "ring-1 ring-accent/40"
              ),
          uploading && "pointer-events-none opacity-80"
        )}
      >
        {featured && (
          <div
            aria-hidden
            className={cn(
              "pointer-events-none absolute inset-x-8 top-0 h-px bg-iridescent opacity-0 transition-opacity duration-300",
              (dragging || uploading) && "opacity-100 animate-shimmer"
            )}
          />
        )}

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
          <div className="relative space-y-5">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-accent" />
            <p className="font-display text-heading-sm font-normal text-ghost-ash">
              Indexing document…
            </p>
            <p className="text-caption text-slate">
              Chunking, embedding, and preparing retrieval
            </p>
            <div className="mx-auto h-1 max-w-xs overflow-hidden rounded-btn bg-charcoal">
              <motion.div
                className="h-full rounded-btn bg-iridescent"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ ease: "easeOut" }}
              />
            </div>
          </div>
        ) : (
          <div className="relative flex flex-col items-center">
            <span
              className={cn(
                "mb-6 flex items-center justify-center rounded-full shadow-inset transition-colors duration-300",
                featured
                  ? "h-16 w-16 bg-midnight group-hover:ring-1 group-hover:ring-ghost-ash/20"
                  : "h-12 w-12 bg-midnight"
              )}
            >
              {featured ? (
                <FileText className="h-7 w-7 text-ghost-ash" strokeWidth={1} />
              ) : (
                <Upload className="h-5 w-5 text-ghost-ash" strokeWidth={1} />
              )}
            </span>
            <p
              className={cn(
                "font-display font-normal text-ghost-ash",
                featured ? "text-heading" : "text-heading-sm"
              )}
            >
              Upload a PDF
            </p>
            <p className="mt-3 text-body text-slate lg:text-subheading">
              Drop your manual here or click to browse
            </p>
            {featured && (
              <p className="mt-6 text-caption text-slate">
                PDF only · up to hundreds of pages
              </p>
            )}
          </div>
        )}
      </motion.div>

      <AnimatePresence>
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-4 text-center text-caption text-accent"
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}
