# LinkedIn Post Draft — DocIntel Release Candidate

---

I’ve been building **DocIntel** — a domain-aware RAG system for large technical PDFs (think CPU architecture manuals, not generic blog posts).

The problem: thousand-page specs full of precise terminology (`CR0.PG`, `#PF`, ordered boot sequences). Generic chatbots hallucinate. Simple vector search misses exact register names.

**What I built:**

→ Hybrid retrieval (HNSW + BM25 + RRF)  
→ Cross-encoder reranking  
→ Authoritative register-definition pinning  
→ Evidence sufficiency gating before generation  
→ Selective answer verification with hallucination mitigation  
→ A **516-case benchmark suite** with automated reports

**Latest benchmark results (local Ollama / Qwen2.5):**

- Recall@K: **95.1%**
- MRR: **0.848**
- Hallucination rate: **4.5%** (down from ~13% pre-Sprint 3)
- Citation accuracy: **70.3%**
- Avg latency: **1854 ms** (verification cut from ~1930 ms → 424 ms via selective verify)

The project reinforced something I care about: **benchmark-driven development**. Fixing a broken NDCG metric (was reporting >100%), auditing citation coverage, and tracing definition failures taught me more than tuning prompts alone.

Stack: Python, FastAPI, Next.js, ChromaDB, Sentence Transformers, BGE reranker, Ollama.

Open-source: [github.com/TensorTorch777/DocIntel](https://github.com/TensorTorch777/DocIntel)

If you work on technical RAG, retrieval evaluation, or grounding — I’d love to connect.

#RAG #LLM #MachineLearning #Retrieval #OpenSource #FastAPI #NLP #Engineering

---

**Optional shorter version:**

Shipped **DocIntel** RC — hybrid RAG for technical manuals with 516-case benchmark suite. **95.1% Recall@K**, **4.5% hallucination rate**, **1854 ms** avg latency. Benchmark-driven dev: fixed NDCG, citation audits, definition failure analysis. #RAG #LLM #OpenSource
