"""Application configuration via environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for DocIntel."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DocIntel"
    app_version: str = "0.1.0"
    debug: bool = False

    # Storage paths
    data_dir: Path = Field(default=Path("./data"))
    upload_dir: Path = Field(default=Path("./data/uploads"))
    chroma_dir: Path = Field(default=Path("./data/chroma"))

    # Chunking — ~600 tokens / ~120 token overlap (char-based approximation)
    chunk_size: int = 2400
    chunk_overlap: int = 480

    # Ingestion performance (0 = auto-detect CPU count)
    pdf_extraction_workers: int = 0
    chunking_workers: int = 0
    embedding_batch_size: int = 256
    embedding_device: str = "auto"  # auto | cuda | cpu
    chroma_index_batch_size: int = 512

    # Retrieval pipeline: hybrid search -> RRF -> entity boost -> rerank -> LLM
    retrieval_candidate_k: int = 20
    retrieval_top_k: int = 5
    reranker_enabled: bool = True
    reranker_model: str = "BAAI/bge-reranker-large"
    hybrid_retrieval_enabled: bool = True
    enable_query_rewrite_llm: bool = False
    entity_boost_weight: float = 0.08
    enable_answer_verification: bool = True
    enable_answer_rewrite: bool = True
    enable_evidence_sufficiency_gate: bool = True
    enable_register_definition_resolver: bool = True
    max_pinned_definition_chunks: int = 3
    definitional_boost_weight: float = 0.12
    unsupported_claim_threshold: float = 0.30

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # LLM (OpenAI-compatible — Ollama / vLLM)
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b"
    llm_timeout_seconds: float = 120.0
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.2
    llm_temperature_technical: float = 0.05

    # ChromaDB collection
    chroma_collection_name: str = "docintel_documents"

    def ensure_directories(self) -> None:
        """Create required directories if they do not exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    settings = Settings()
    settings.ensure_directories()
    return settings
