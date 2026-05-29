"use client";

import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface HeroProps {
  hasDocument: boolean;
  onGetStarted: () => void;
}

export function Hero({ hasDocument, onGetStarted }: HeroProps) {
  if (hasDocument) {
    return (
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="border-b border-ghost-border bg-paper-white px-6 py-8 lg:px-8"
      >
        <div className="mx-auto max-w-page">
          <Badge variant="accent">RAG Pipeline Active</Badge>
          <h1 className="mt-3 font-display text-heading-lg font-medium tracking-tight text-midnight-ink">
            Query your document
          </h1>
          <p className="mt-2 max-w-2xl text-body text-muted-ash">
            Ask questions, generate summaries, or scan for anomalies — all
            grounded in your indexed report with live streaming responses.
          </p>
        </div>
      </motion.section>
    );
  }

  return (
    <section className="relative overflow-hidden border-b border-ghost-border bg-grid-pattern bg-grid">
      <div className="mx-auto max-w-page px-6 py-20 text-center lg:px-8 lg:py-28">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Badge variant="accent" className="mb-6">
            GenAI Document Intelligence
          </Badge>
          <h1 className="mx-auto max-w-4xl font-display text-display font-medium tracking-tight text-midnight-ink md:text-[56px] lg:text-[72px] lg:leading-[0.97] lg:tracking-[-1.44px]">
            Turn hundred-page reports into answers
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-subheading text-muted-ash">
            Upload engineering PDFs, index with ChromaDB, and query with
            grounded RAG — streaming responses powered by Qwen2.5.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Button onClick={onGetStarted}>Upload a document</Button>
            <Button variant="secondary" onClick={onGetStarted}>
              Try the demo
            </Button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
