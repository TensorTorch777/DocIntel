"use client";

import { useCallback, useEffect, useState } from "react";
import type { StoredDocument } from "@/lib/types";

const STORAGE_KEY = "docintel_documents";

export function useDocuments() {
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as StoredDocument[];
        setDocuments(parsed);
        if (parsed.length > 0) setActiveId(parsed[0].document_id);
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const persist = useCallback((docs: StoredDocument[]) => {
    setDocuments(docs);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(docs));
  }, []);

  const addDocument = useCallback(
    (doc: StoredDocument) => {
      persist([doc, ...documents.filter((d) => d.document_id !== doc.document_id)]);
      setActiveId(doc.document_id);
    },
    [documents, persist]
  );

  const removeDocument = useCallback(
    (id: string) => {
      const next = documents.filter((d) => d.document_id !== id);
      persist(next);
      if (activeId === id) setActiveId(next[0]?.document_id ?? null);
    },
    [activeId, documents, persist]
  );

  const activeDocument = documents.find((d) => d.document_id === activeId) ?? null;

  return {
    documents,
    activeId,
    activeDocument,
    setActiveId,
    addDocument,
    removeDocument,
  };
}
