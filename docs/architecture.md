# DocIntel Architecture

Domain-aware technical RAG pipeline for large PDF manuals. This document describes retrieval, grounding, and benchmark evaluation flows.

---

## Retrieval flow

```mermaid
flowchart TB
    subgraph Input
        Q[User query]
    end

    subgraph Preprocess
        PRE[Query preprocess]
        EXP[Query expansion]
        ENT[Entity extraction]
    end

    subgraph Retrieve
        VEC[Vector search HNSW top-20]
        BM25[BM25 keyword top-20]
        DEF[Definition resolver scan]
    end

    subgraph Fuse
        RRF[RRF merge]
        BOOST[Entity + definitional boost]
        RER[Cross-encoder rerank]
        PIN[Pin authoritative definitions]
        SORT[Definition-first sort]
    end

    subgraph Output
        TOPK[Top-K chunks + context]
    end

    Q --> PRE --> EXP --> ENT
    ENT --> VEC
    ENT --> BM25
    ENT --> DEF
    VEC --> RRF
    BM25 --> RRF
    DEF --> PIN
    RRF --> BOOST --> RER --> PIN --> SORT --> TOPK
```

### Key modules

| Module | Path | Role |
|--------|------|------|
| Query preprocess | `app/services/query_preprocess.py` | Strip prompt noise |
| Query rewriter | `app/services/query_rewriter.py` | Register/alias expansion |
| Vector store | `app/services/vector_store.py` | ChromaDB HNSW |
| BM25 store | `app/services/bm25_store.py` | Per-document keyword index |
| Definition resolver | `app/services/register_definition_resolver.py` | Authoritative definition pinning |
| Reranker | `app/services/reranker.py` | Cross-encoder scoring |
| Retrieval orchestrator | `app/services/retrieval.py` | Full hybrid pipeline |

---

## Grounding flow

```mermaid
flowchart TB
    TOPK[Retrieved context] --> GATE{Evidence sufficiency gate}
    GATE -->|Insufficient| ABST[Abstain message]
    GATE -->|Sufficient| GEN[LLM generation]
    GEN --> PROC{Procedural query?}
    PROC -->|Yes| STEPS[Step extract + filter + format]
    PROC -->|No| QA[Grounded QA prompt]
    STEPS --> CITE[Inline Source N citations]
    QA --> CITE
    CITE --> RISK{Risk assessment}
    RISK -->|Low / authoritative| SKIP[Skip verification]
    RISK -->|Medium| LIGHT[Lightweight claim verify]
    RISK -->|High| FULL[Full LLM verify]
    LIGHT --> ACT{Unsupported claims?}
    FULL --> ACT
    ACT -->|Yes| RW[Rewrite / conservative regen]
    ACT -->|No| OUT[Final answer]
    RW --> OUT
    SKIP --> OUT
```

### Grounding controls

| Control | Purpose |
|---------|---------|
| Evidence sufficiency gate | Blocks generation when weighted coverage is below threshold |
| QA system prompt | Requires `[Source N]` per factual claim |
| Procedural path | Template `Step N:` answers with mandatory citations |
| Answer verification | LLM JSON verify for unsupported claims |
| Selective verification | Skips ~50% of low-risk cases (Sprint 3) |
| Conservative rewrite | Regenerates when unsupported ratio exceeds threshold |

### Citation model

Sources are numbered `1..K` in context order (`format_context` in `retrieval.py`). Answers must cite `[Source N]` inline. Benchmark citation metrics measure sentence coverage, valid indices, and lexical alignment (`app/services/citation_support.py`).

---

## Benchmark flow

```mermaid
flowchart LR
    CASES[benchmark_cases.json] --> RUNNER[benchmark_runner.py]
    RUNNER --> PIPE[Pipeline modes]
    PIPE --> EVAL[RAGService.evaluate_query]
    EVAL --> METRICS[benchmark/metrics.py]
    METRICS --> JSON[benchmark_results.json]
    METRICS --> CSV[benchmark_results.csv]
    JSON --> REPORTS[generate_report.py]
    JSON --> DEF[definition_failure_analysis.py]
    JSON --> CIT[citation_audit.py]
    REPORTS --> PLOTS[reports/plots/*.png]
```

### Benchmark categories (516 cases)

| Category | Count | Focus |
|----------|------:|-------|
| definition_queries | 132 | Register/flag definitions |
| entity_collision_queries | 60 | Disambiguation |
| procedural_queries | 37 | Ordered steps |
| multihop_queries | 80 | Multi-chunk reasoning |
| adversarial_queries | 54 | Prompt injection resistance |
| insufficient_evidence_queries | 46 | Abstention behavior |

### Metrics tracked

- **Retrieval:** Recall@K, MRR, NDCG@K (capped at 1.0)
- **Quality:** must_contain, hallucination rate, citation accuracy
- **Definition funnel:** retrieved → selected → used → correct
- **Procedural:** ordered step accuracy, extra step rate, precision/recall
- **Latency:** retrieval, rerank, generation, verification (per stage)

---

## Configuration

Primary settings in `.env` — see `.env.example` for coverage weights, verification cache, procedural limits, and pipeline toggles.
