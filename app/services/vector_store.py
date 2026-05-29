"""ChromaDB vector store with HNSW index."""

import logging
from dataclasses import dataclass
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import Settings
from app.utils.exceptions import DocumentNotFoundError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned from similarity search."""

    chunk_id: str
    text: str
    page_number: int | None
    chunk_index: int
    score: float
    metadata: dict[str, Any]


class VectorStoreService:
    """Persist and retrieve document embeddings via ChromaDB."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = chromadb.PersistentClient(
            path=str(settings.chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={
                "hnsw:space": "cosine",
                "hnsw:construction_ef": 128,
                "hnsw:search_ef": 64,
                "hnsw:M": 16,
            },
        )

    def index_document(
        self,
        document_id: str,
        chunk_ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> int:
        """
        Upsert chunks for a document into the vector store.

        Returns:
            Number of chunks indexed.
        """
        if not chunk_ids:
            return 0

        # Remove any prior version of this document
        self.delete_document(document_id)

        batch_size = self._settings.chroma_index_batch_size
        total = len(chunk_ids)

        for start in range(0, total, batch_size):
            end = start + batch_size
            self._collection.add(
                ids=chunk_ids[start:end],
                documents=texts[start:end],
                embeddings=embeddings[start:end],
                metadatas=metadatas[start:end],
            )

        logger.info(
            "Indexed %d chunks for document %s (batch_size=%d)",
            total,
            document_id,
            batch_size,
        )
        return total

    def retrieve(
        self,
        document_id: str,
        query_embedding: list[float],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve top-k most similar chunks for a document.

        Args:
            document_id: Filter results to this document.
            query_embedding: Query vector.
            top_k: Number of results (defaults to settings.retrieval_top_k).

        Returns:
            Ranked list of RetrievedChunk objects.

        Raises:
            DocumentNotFoundError: If no chunks exist for the document.
        """
        k = top_k or self._settings.retrieval_top_k

        if not self.document_exists(document_id):
            raise DocumentNotFoundError(f"Document '{document_id}' not found in index")

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where={"document_id": document_id},
            include=["documents", "metadatas", "distances"],
        )

        ids = results["ids"][0] if results["ids"] else []
        if not ids:
            raise DocumentNotFoundError(
                f"No indexed chunks found for document '{document_id}'"
            )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        chunks: list[RetrievedChunk] = []
        for idx, chunk_id in enumerate(ids):
            meta = metadatas[idx] or {}
            # Chroma returns cosine distance; convert to similarity score
            distance = distances[idx]
            score = 1.0 - distance

            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=documents[idx],
                    page_number=meta.get("page_number"),
                    chunk_index=meta.get("chunk_index", idx),
                    score=score,
                    metadata=meta,
                )
            )

        return chunks

    def get_all_chunks(self, document_id: str, limit: int = 50) -> list[RetrievedChunk]:
        """Fetch chunks for summarization (broader context sampling)."""
        if not self.document_exists(document_id):
            raise DocumentNotFoundError(f"Document '{document_id}' not found in index")

        results = self._collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
            limit=limit,
        )

        chunks: list[RetrievedChunk] = []
        for idx, chunk_id in enumerate(results["ids"]):
            meta = results["metadatas"][idx] or {}
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=results["documents"][idx],
                    page_number=meta.get("page_number"),
                    chunk_index=meta.get("chunk_index", idx),
                    score=1.0,
                    metadata=meta,
                )
            )
        return sorted(chunks, key=lambda c: c.chunk_index)

    def document_exists(self, document_id: str) -> bool:
        """Check whether a document has indexed chunks."""
        results = self._collection.get(
            where={"document_id": document_id},
            limit=1,
            include=[],
        )
        return bool(results["ids"])

    def get_document_info(self, document_id: str) -> dict[str, Any] | None:
        """Return metadata stored for a document."""
        results = self._collection.get(
            where={"document_id": document_id},
            include=["metadatas"],
        )
        if not results["ids"]:
            return None

        first_meta = results["metadatas"][0] or {}
        return {
            "document_id": document_id,
            "filename": first_meta.get("filename", "unknown"),
            "page_count": first_meta.get("page_count", 0),
            "chunk_count": len(results["ids"]),
        }

    def delete_document(self, document_id: str) -> None:
        """Remove all chunks belonging to a document."""
        results = self._collection.get(
            where={"document_id": document_id},
            include=[],
        )
        if results["ids"]:
            self._collection.delete(ids=results["ids"])
            logger.info("Deleted %d chunks for document %s", len(results["ids"]), document_id)
