<div align="center">

# DocIntel

**Domain-aware technical RAG for large-scale manuals**

Hybrid retrieval · evidence gating · verification

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

</div>

---

## Overview

DocIntel is a **document-grounded question-answering system** built for dense technical PDFs — CPU architecture manuals, safety specifications, and engineering references where exact register names, bit positions, and procedural sequences matter.

Unlike generic RAG demos, DocIntel combines **keyword + vector hybrid retrieval**, **cross-encoder reranking**, **authoritative definition pinning**, **evidence sufficiency gating**, and **selective answer verification** to reduce hallucinations while keeping latency practical on local hardware (Ollama / Qwen2.5).

---

## Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontSize': '16px', 'fontFamily': 'Segoe UI, system-ui, sans-serif', 'lineColor': '#94A3B8'}}}%%
flowchart TB
    Q(["User Query"])

    subgraph S1["Query Understanding"]
        direction TB
        QE["Query Expansion<br/>register aliases · entity detection"]
    end

    subgraph S2["Retrieval Pipeline"]
        direction TB
        HR["Hybrid Retrieval<br/>HNSW vector + BM25 keyword"]
        RRF["RRF Fusion<br/>reciprocal rank merge"]
        RER["Cross-Encoder Rerank<br/>bge-reranker-large"]
        DR["Definition Resolver<br/>pin authoritative definitions"]
    end

    subgraph S3["Grounded Generation"]
        direction TB
        EG{"Evidence Gate<br/>weighted coverage check"}
        LLM["LLM Generation<br/>Ollama · Qwen2.5"]
    end

    subgraph S4["Quality & Output"]
        direction TB
        VER["Verification<br/>selective · cached · risk-based"]
        ANS(["Final Answer<br/>cited · grounded"])
    end

    Q --> QE
    QE --> HR
    HR --> RRF
    RRF --> RER
    RER --> DR
    DR --> EG
    EG -->|sufficient| LLM
    EG -->|insufficient| ANS
    LLM --> VER
    VER --> ANS

    style Q fill:#4338CA,stroke:#3730A3,color:#FFFFFF,stroke-width:2px
    style ANS fill:#047857,stroke:#065F46,color:#FFFFFF,stroke-width:2px

    style S1 fill:#F5F3FF,stroke:#A5B4FC,color:#312E81,stroke-width:1.5px
    style S2 fill:#EFF6FF,stroke:#93C5FD,color:#1E3A5F,stroke-width:1.5px
    style S3 fill:#ECFDF5,stroke:#6EE7B7,color:#064E3B,stroke-width:1.5px
    style S4 fill:#FFFBEB,stroke:#FCD34D,color:#78350F,stroke-width:1.5px

    style QE fill:#FFFFFF,stroke:#6366F1,color:#312E81,stroke-width:1.5px
    style HR fill:#FFFFFF,stroke:#3B82F6,color:#1E3A5F,stroke-width:1.5px
    style RRF fill:#FFFFFF,stroke:#2563EB,color:#1E3A5F,stroke-width:1.5px
    style RER fill:#FFFFFF,stroke:#1D4ED8,color:#1E3A5F,stroke-width:1.5px
    style DR fill:#FFFFFF,stroke:#0EA5E9,color:#0C4A6E,stroke-width:1.5px

    style EG fill:#FEF3C7,stroke:#D97706,color:#78350F,stroke-width:1.5px
    style LLM fill:#FFFFFF,stroke:#059669,color:#064E3B,stroke-width:1.5px

    style VER fill:#FFFFFF,stroke:#EA580C,color:#7C2D12,stroke-width:1.5px
```

| Stage | Implementation |
|-------|----------------|
| Query expansion | Rule-based register/entity expansion (`query_rewriter`) |
| Hybrid retrieval | ChromaDB HNSW + BM25, top-20 each |
| RRF | Reciprocal rank fusion (`k=60`) |
| Rerank | `BAAI/bge-reranker-large` cross-encoder |
| Definition resolver | Pins authoritative register-definition chunks |
| Evidence gate | Weighted coverage thresholds before generation |
| LLM | OpenAI-compatible API (Ollama `qwen2.5:7b`) |
| Verification | Risk-based selective verify + cache |

---

## Features

- **Hybrid retrieval** — vector + BM25 with RRF merge
- **Cross-encoder reranking** — precision-focused top-k selection
- **Register definition resolver** — pins authoritative definition passages
- **Evidence sufficiency gating** — abstains when coverage is insufficient
- **Procedural reasoning** — query-aware step extraction and ordering
- **Selective verification** — skips low-risk / authoritative-definition answers
- **Hallucination mitigation** — claim verification + conservative rewrite path

---

## Running Locally

### Prerequisites

- Python 3.12+
- Node.js 20+
- [Ollama](https://ollama.com) with `qwen2.5:7b`
- Optional: CUDA GPU for embeddings/reranking

```bash
ollama pull qwen2.5:7b
```

### 1. Clone and configure

```bash
git clone https://github.com/TensorTorch777/DocIntel.git
cd DocIntel
cp .env.example .env
```

### 2. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open **http://localhost:3000** — upload a PDF, wait for indexing, then chat.

---

## Project structure

```
DocIntel/
├── app/                    # FastAPI backend (RAG, retrieval, verification)
├── frontend/               # Next.js 14 UI
└── main.py                 # API entry point
```

---

## License

MIT — see [LICENSE](LICENSE).
