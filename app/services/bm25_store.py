"""BM25 keyword index for hybrid retrieval."""

import logging
import pickle
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.config import Settings
from app.services.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"\b[\w#\.]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_PATTERN.findall(text) if len(t) > 1]


@dataclass
class _BM25Index:
    chunk_ids: list[str]
    texts: list[str]
    metadatas: list[dict]
    bm25: BM25Okapi


class BM25Store:
    """Per-document BM25 indexes persisted to disk."""

    def __init__(self, settings: Settings) -> None:
        self._dir = settings.data_dir / "bm25"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, _BM25Index] = {}

    def _path(self, document_id: str) -> Path:
        return self._dir / f"{document_id}.pkl"

    def build(
        self,
        document_id: str,
        chunk_ids: list[str],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        """Build and persist BM25 index for a document."""
        tokenized = [_tokenize(t) for t in texts]
        index = _BM25Index(
            chunk_ids=chunk_ids,
            texts=texts,
            metadatas=metadatas,
            bm25=BM25Okapi(tokenized),
        )
        self._cache[document_id] = index
        with open(self._path(document_id), "wb") as f:
            pickle.dump(index, f)
        logger.info("Built BM25 index for %s (%d chunks)", document_id, len(chunk_ids))

    def delete(self, document_id: str) -> None:
        """Remove BM25 index for a document."""
        self._cache.pop(document_id, None)
        path = self._path(document_id)
        if path.exists():
            path.unlink()

    def _load(self, document_id: str) -> _BM25Index | None:
        if document_id in self._cache:
            return self._cache[document_id]
        path = self._path(document_id)
        if not path.exists():
            return None
        with open(path, "rb") as f:
            index = pickle.load(f)
        self._cache[document_id] = index
        return index

    def search(
        self,
        document_id: str,
        query: str,
        top_k: int = 20,
    ) -> list[RetrievedChunk]:
        """BM25 keyword search over document chunks."""
        index = self._load(document_id)
        if index is None:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = index.bm25.get_scores(tokens)
        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        chunks: list[RetrievedChunk] = []
        for idx, score in ranked:
            if score <= 0:
                continue
            meta = dict(index.metadatas[idx])
            meta["bm25_score"] = float(score)
            meta["retrieval_method"] = "bm25"
            chunks.append(
                RetrievedChunk(
                    chunk_id=index.chunk_ids[idx],
                    text=index.texts[idx],
                    page_number=meta.get("page_number"),
                    chunk_index=meta.get("chunk_index", idx),
                    score=float(score),
                    metadata=meta,
                )
            )
        return chunks

    def get_all_chunks(self, document_id: str) -> list[RetrievedChunk]:
        """Return all indexed chunks for definition resolution scans."""
        index = self._load(document_id)
        if index is None:
            return []

        chunks: list[RetrievedChunk] = []
        for idx, chunk_id in enumerate(index.chunk_ids):
            meta = dict(index.metadatas[idx])
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=index.texts[idx],
                    page_number=meta.get("page_number"),
                    chunk_index=meta.get("chunk_index", idx),
                    score=0.0,
                    metadata=meta,
                )
            )
        return chunks
