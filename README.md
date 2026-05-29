# DocIntel

GenAI document intelligence for large technical PDFs. Upload multi-thousand-page manuals, index them with hybrid RAG, and query with grounded Q&A, summarization, and anomaly detection — powered by local LLM inference (Ollama / Qwen2.5).

## Features

- **PDF ingestion** — PyMuPDF extraction, LangChain chunking, parallel processing, page-aware metadata
- **Hybrid retrieval** — ChromaDB HNSW vector search + BM25 keyword search, RRF merge, cross-encoder reranking
- **Register-definition pinning** — authoritative definition chunks for `CR0.PG`, `CR4.PGE`, `IA32_EFER.NXE`, etc.
- **Grounded Q&A** — strict prompts, evidence sufficiency gating, claim verification, conservative rewrite
- **Summarization & anomaly detection** — document-wide analysis with source citations
- **Benchmark mode** — repeatable retrieval and grounding evaluation
- **Streaming UI** — Next.js frontend with SSE token streaming and retrieval debug panel

## Architecture

```
User query
  → query preprocessing & expansion
  → register definition resolver (pinned authoritative chunks)
  → vector search (HNSW) + BM25 keyword search
  → RRF merge → entity boost → definitional boost
  → cross-encoder rerank (BAAI/bge-reranker-large)
  → evidence sufficiency gate
  → LLM generation → verification → optional rewrite
```

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.12 |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Vector store | ChromaDB (HNSW, cosine) |
| Keyword index | BM25 (rank-bm25) |
| Embeddings | Sentence Transformers |
| Reranker | Cross-encoder (bge-reranker-large) |
| LLM | OpenAI-compatible API (Ollama + Qwen2.5) |

## Quick start

### Prerequisites

- Python 3.12+
- Node.js 20+
- [Ollama](https://ollama.com) with `qwen2.5:7b` pulled
- Optional: NVIDIA GPU for faster embeddings

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), upload a PDF, and start asking questions.

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Upload and index a PDF |
| `POST` | `/chat` | Streaming RAG chat (SSE) |
| `POST` | `/summarize` | Document summarization |
| `POST` | `/anomaly` | Anomaly scan |
| `POST` | `/benchmark/run` | RAG benchmark suite |
| `GET` | `/health` | Health check |

## Project structure

```
DocIntel/
├── app/                 # FastAPI backend
│   ├── routers/         # API routes
│   ├── services/        # ingestion, retrieval, RAG, reranker, BM25
│   └── models/          # Pydantic schemas
├── frontend/            # Next.js UI
├── main.py
├── requirements.txt
└── .env.example
```

Runtime data (`data/`, ChromaDB indexes, uploads) is gitignored — created locally on first upload.

## Configuration

Copy `.env.example` to `.env` and adjust:

- `LLM_BASE_URL` / `LLM_MODEL` — Ollama or any OpenAI-compatible endpoint
- `EMBEDDING_DEVICE` — `cuda` or `cpu`
- `RERANKER_MODEL` — cross-encoder for reranking
- `ENABLE_EVIDENCE_SUFFICIENCY_GATE` — pre-generation evidence gate
- `ENABLE_REGISTER_DEFINITION_RESOLVER` — pin authoritative register definitions

## License

MIT — see [LICENSE](LICENSE).
