# Resume Bullets — DocIntel

Use these for LinkedIn, CV, or portfolio. All benchmark numbers from `benchmark/results/sprint3_full_516/` (516 cases).

---

## One-line

Built **DocIntel**, a domain-aware RAG system for technical PDFs with hybrid retrieval, evidence gating, and verification — **95.1% Recall@K**, **4.5% hallucination rate** on a 516-case benchmark.

---

## Two-line

Engineered **DocIntel**, a production-style RAG pipeline (FastAPI + Next.js) for thousand-page technical manuals with HNSW + BM25 hybrid search, cross-encoder reranking, and register-definition pinning.

Achieved **95.1% Recall@K** and **4.5% hallucination rate** on 516 benchmark cases; reduced end-to-end latency **46%** (3424 ms → 1854 ms) via selective verification.

---

## Detailed (resume / portfolio)

**DocIntel — Domain-Aware Technical RAG System**  
*Python · FastAPI · Next.js · ChromaDB · Ollama · Qwen2.5*

- Designed and implemented a **hybrid retrieval pipeline** (vector HNSW + BM25 + RRF + cross-encoder rerank) for dense CPU architecture manuals with exact register/flag terminology requirements.
- Built an **authoritative definition resolver** that pins register-definition chunks and sorts context definition-first, improving grounding for `CR0.PG`, `IA32_EFER.NXE`, and related entities.
- Added **evidence sufficiency gating** with weighted coverage (definition / behavior / exceptions / interactions) to abstain before generation when retrieval is insufficient.
- Implemented **procedural reasoning** with query-aware step filtering, dependency ordering, and mandatory `[Source N]` citations for sequence queries.
- Shipped **selective answer verification** (risk-based skip, LRU cache, lightweight claim extraction) cutting verification latency **78%** (1930 ms → 424 ms) while holding Recall@K at **95.1%**.
- Authored a **516-case benchmark suite** across definition, procedural, multihop, adversarial, and abstention categories with automated reports, NDCG fix, citation audit, and definition failure analysis.
- **Results:** Recall@K **95.1%**, MRR **0.848**, hallucination **4.5%**, citation accuracy **70.3%**, avg latency **1854 ms**.

---

## Skills tags

`Retrieval-Augmented Generation` · `Hybrid Search` · `BM25` · `Vector Search` · `Cross-Encoder Reranking` · `LLM Grounding` · `Hallucination Mitigation` · `FastAPI` · `Next.js` · `Benchmark Engineering` · `Technical Documentation`

---

## Talking points (interviews)

1. **Why hybrid retrieval?** — Technical manuals require both semantic paraphrase matching (vector) and exact token hits (`CR0.PG`, `#PF`).
2. **How do you measure hallucinations?** — Composite: must_not violations, unsupported claim ratio from verifier, must_contain misses on non-abstention cases.
3. **Biggest RC learning** — Definition accuracy metric (34.5%) diverges from must_contain (61.9%); benchmark credibility required funnel analysis and citation audits, not just headline scores.
4. **Latency win** — Skip verification when authoritative definitions are fully cited; cache verify results for repeated queries.
