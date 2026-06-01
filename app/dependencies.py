"""FastAPI dependency injection."""

from functools import lru_cache

from app.config import Settings, get_settings
from app.services.bm25_store import BM25Store
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.services.ingestion import IngestionService
from app.services.llm import LLMService
from app.services.pdf_extractor import PDFExtractor
from app.services.rag import RAGService
from app.services.reranker import RerankerService
from app.services.retrieval import RetrievalService
from app.services.vector_store import VectorStoreService


@lru_cache
def get_pdf_extractor() -> PDFExtractor:
    settings = get_settings()
    workers = settings.pdf_extraction_workers or 0
    return PDFExtractor(workers=workers)


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(get_settings())


@lru_cache
def get_vector_store() -> VectorStoreService:
    return VectorStoreService(get_settings())


@lru_cache
def get_bm25_store() -> BM25Store:
    return BM25Store(get_settings())


@lru_cache
def get_chunking_service() -> ChunkingService:
    return ChunkingService(get_settings())


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService(get_settings())


@lru_cache
def get_reranker_service() -> RerankerService:
    return RerankerService(get_settings())


@lru_cache
def get_retrieval_service() -> RetrievalService:
    settings = get_settings()
    return RetrievalService(
        settings=settings,
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
        bm25_store=get_bm25_store(),
        reranker_service=get_reranker_service(),
        llm_service=get_llm_service(),
    )


@lru_cache
def get_rag_service() -> RAGService:
    return RAGService(
        settings=get_settings(),
        retrieval_service=get_retrieval_service(),
        llm_service=get_llm_service(),
    )


@lru_cache
def get_ingestion_service() -> IngestionService:
    settings = get_settings()
    return IngestionService(
        settings=settings,
        pdf_extractor=get_pdf_extractor(),
        chunking_service=get_chunking_service(),
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
        bm25_store=get_bm25_store(),
    )


def get_app_settings() -> Settings:
    return get_settings()
