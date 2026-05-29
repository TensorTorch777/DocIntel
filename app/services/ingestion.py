"""Document ingestion orchestration."""

import asyncio
import logging
import time
import uuid
from pathlib import Path

from app.config import Settings
from app.models.schemas import UploadResponse
from app.services.bm25_store import BM25Store
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.services.pdf_extractor import PDFExtractor
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrate PDF upload, extraction, chunking, and indexing."""

    def __init__(
        self,
        settings: Settings,
        pdf_extractor: PDFExtractor,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreService,
        bm25_store: BM25Store,
    ) -> None:
        self._settings = settings
        self._pdf_extractor = pdf_extractor
        self._chunking = chunking_service
        self._embeddings = embedding_service
        self._vector_store = vector_store
        self._bm25 = bm25_store

    async def ingest_pdf(self, filename: str, file_bytes: bytes) -> UploadResponse:
        """
        Save, extract, chunk, embed, and index a PDF document.

        Heavy CPU/GPU work runs in a thread pool so the event loop stays responsive.

        Args:
            filename: Original upload filename.
            file_bytes: Raw PDF bytes.

        Returns:
            UploadResponse with document metadata.
        """
        return await asyncio.to_thread(self._ingest_pdf_sync, filename, file_bytes)

    def _ingest_pdf_sync(self, filename: str, file_bytes: bytes) -> UploadResponse:
        """Synchronous ingestion pipeline with per-phase timing logs."""
        t0 = time.perf_counter()
        document_id = str(uuid.uuid4())
        safe_name = Path(filename).name
        save_path = self._settings.upload_dir / f"{document_id}_{safe_name}"

        save_path.write_bytes(file_bytes)
        logger.info("Saved upload to %s", save_path)

        t1 = time.perf_counter()
        extracted = self._pdf_extractor.extract(save_path)
        t2 = time.perf_counter()

        pages = [(p.page_number, p.text) for p in extracted.pages]
        chunks = self._chunking.chunk_document(document_id, pages)
        if not chunks:
            raise ValueError("Chunking produced zero chunks from document text")
        t3 = time.perf_counter()

        texts = [c.text for c in chunks]
        embeddings = self._embeddings.embed_texts(texts)
        t4 = time.perf_counter()

        metadatas = [
            {
                "document_id": document_id,
                "filename": safe_name,
                "page_count": extracted.page_count,
                "page_number": c.page_number,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]

        chunk_count = self._vector_store.index_document(
            document_id=document_id,
            chunk_ids=[c.chunk_id for c in chunks],
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        self._bm25.build(document_id, [c.chunk_id for c in chunks], texts, metadatas)
        t5 = time.perf_counter()

        logger.info(
            "Ingestion timing for %s — extract: %.1fs, chunk: %.1fs, "
            "embed (%s, batch=%d): %.1fs, index: %.1fs, total: %.1fs",
            safe_name,
            t2 - t1,
            t3 - t2,
            self._embeddings.device,
            self._settings.embedding_batch_size,
            t4 - t3,
            t5 - t4,
            t5 - t0,
        )

        return UploadResponse(
            document_id=document_id,
            filename=safe_name,
            page_count=extracted.page_count,
            chunk_count=chunk_count,
        )
