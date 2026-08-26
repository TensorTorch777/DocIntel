"use client";

import { Button } from "@/components/ui/Button";
import { formatNumber } from "@/lib/utils";
import type { StoredDocument } from "@/lib/types";
import { Loader2, RefreshCw } from "lucide-react";

interface DocumentSummaryProps {
  document: StoredDocument;
  uploading?: boolean;
  onReplace: () => void;
}

export function DocumentSummary({
  document,
  uploading,
  onReplace,
}: DocumentSummaryProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-charcoal px-6 py-3 md:px-12 lg:px-16 xl:px-24 2xl:px-32">
      <div className="min-w-0">
        <p className="truncate font-display text-body font-normal text-ghost-ash">
          {document.filename.replace(/\.(pdf|png|jpe?g|webp|gif|wav|m4a|mp3|mp4|mov|webm)$/i, "")}
        </p>
        <p className="text-caption text-slate">
          {document.modality && document.modality !== "pdf"
            ? `${document.modality} · `
            : ""}
          {formatNumber(document.page_count)}{" "}
          {document.modality === "audio"
            ? "track"
            : document.modality === "video"
              ? "segments"
              : document.modality === "image"
                ? "image"
                : "pages"}{" "}
          · {formatNumber(document.chunk_count)} chunks
        </p>
      </div>

      <Button
        variant="ghost"
        className="shrink-0 text-caption"
        onClick={onReplace}
        disabled={uploading}
      >
        {uploading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        Replace
      </Button>
    </div>
  );
}
