"use client";

import { motion } from "framer-motion";
import { Card } from "@/components/ui/Card";
import { Database, FileText, Sparkles, Zap } from "lucide-react";

const features = [
  {
    icon: FileText,
    title: "PDF Ingestion",
    description:
      "PyMuPDF extraction for multi-hundred-page reports with page-aware chunk metadata.",
  },
  {
    icon: Database,
    title: "Vector Indexing",
    description:
      "ChromaDB HNSW index with Sentence Transformers embeddings for top-k retrieval.",
  },
  {
    icon: Sparkles,
    title: "Grounded RAG",
    description:
      "Q&A, summarization, and anomaly detection strictly grounded in retrieved context.",
  },
  {
    icon: Zap,
    title: "Live Streaming",
    description:
      "Server-Sent Events deliver token-by-token responses from local Qwen2.5 inference.",
  },
];

export function Features() {
  return (
    <section id="features" className="mx-auto max-w-page px-6 py-section lg:px-8">
      <div className="mb-10 text-center">
        <h2 className="font-display text-heading-lg font-medium tracking-tight text-midnight-ink">
          Engineered for precision
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-body text-muted-ash">
          A full-stack document intelligence pipeline — from ingestion to
          streaming generation.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {features.map((feature, i) => {
          const Icon = feature.icon;
          return (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
            >
              <Card className="h-full">
                <Icon className="h-5 w-5 text-electric-violet" />
                <h3 className="mt-4 font-display text-heading-sm font-medium text-midnight-ink">
                  {feature.title}
                </h3>
                <p className="mt-2 text-caption text-muted-ash leading-relaxed">
                  {feature.description}
                </p>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
