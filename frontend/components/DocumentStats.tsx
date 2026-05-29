"use client";

import { motion } from "framer-motion";
import { Card } from "@/components/ui/Card";
import { formatNumber } from "@/lib/utils";
import type { StoredDocument } from "@/lib/types";
import { BookOpen, Layers, Hash } from "lucide-react";

interface DocumentStatsProps {
  document: StoredDocument | null;
}

const stats = [
  { key: "pages", icon: BookOpen, label: "Pages" },
  { key: "chunks", icon: Layers, label: "Chunks" },
  { key: "id", icon: Hash, label: "Document ID" },
] as const;

export function DocumentStats({ document }: DocumentStatsProps) {
  if (!document) return null;

  const values = {
    pages: formatNumber(document.page_count),
    chunks: formatNumber(document.chunk_count),
    id: document.document_id.slice(0, 8) + "…",
  };

  return (
    <div className="grid grid-cols-3 gap-4">
      {stats.map(({ key, icon: Icon, label }, i) => (
        <motion.div
          key={key}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.08 }}
        >
          <Card elevated className="!p-4">
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-electric-violet" />
              <span className="text-caption text-muted-ash">{label}</span>
            </div>
            <p className="mt-2 font-display text-heading-sm font-medium text-midnight-ink">
              {values[key]}
            </p>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
