"use client";

import { useCallback, useEffect, useRef } from "react";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { UploadPanel } from "@/components/UploadPanel";
import { ChatPanel } from "@/components/ChatPanel";
import { Features } from "@/components/Features";
import { useDocuments } from "@/hooks/useDocuments";
import { checkHealth } from "@/lib/api";
import { useState } from "react";

export function DocIntelApp() {
  const {
    documents,
    activeId,
    activeDocument,
    setActiveId,
    addDocument,
    removeDocument,
  } = useDocuments();

  const [apiOnline, setApiOnline] = useState(false);
  const workspaceRef = useRef<HTMLElement>(null);

  useEffect(() => {
    checkHealth().then(setApiOnline);
    const interval = setInterval(() => checkHealth().then(setApiOnline), 15000);
    return () => clearInterval(interval);
  }, []);

  const scrollToWorkspace = useCallback(() => {
    workspaceRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  return (
    <div className="min-h-screen">
      <Header apiOnline={apiOnline} onUploadClick={scrollToWorkspace} />
      <Hero hasDocument={documents.length > 0} onGetStarted={scrollToWorkspace} />

      <section
        id="workspace"
        ref={workspaceRef}
        className="mx-auto max-w-page px-6 py-section lg:px-8"
      >
        <div className="grid gap-8 lg:grid-cols-[380px_1fr]">
          <UploadPanel
            documents={documents}
            activeId={activeId}
            onSelect={setActiveId}
            onUploaded={addDocument}
            onRemove={removeDocument}
          />
          <ChatPanel document={activeDocument} />
        </div>
      </section>

      <Features />

      <footer className="border-t border-ghost-border py-8 text-center text-caption text-muted-ash">
        DocIntel · FastAPI · ChromaDB · Qwen2.5 · Next.js 14
      </footer>
    </div>
  );
}
