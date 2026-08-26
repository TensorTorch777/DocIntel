"use client";

import { motion } from "framer-motion";
import { formatNumber } from "@/lib/utils";
import type { StoredDocument } from "@/lib/types";

interface DocumentStatsProps {
  document: StoredDocument | null;
}

export function DocumentStats({ document }: DocumentStatsProps) {
  if (!document) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-wrap gap-4 border-b border-charcoal px-6 py-3 md:px-8"
    >
      <div>
        <p className="text-caption text-slate">
          {document.modality && document.modality !== "pdf" ? "Modality" : "Pages"}
        </p>
        <p className="font-display text-heading-sm font-normal text-ghost-ash">
          {document.modality && document.modality !== "pdf"
            ? document.modality
            : formatNumber(document.page_count)}
        </p>
      </div>
      <div>
        <p className="text-caption text-slate">Chunks</p>
        <p className="font-display text-heading-sm font-normal text-ghost-ash">
          {formatNumber(document.chunk_count)}
        </p>
      </div>
    </motion.div>
  );
}
