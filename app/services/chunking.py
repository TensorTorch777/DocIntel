"""Recursive text chunking optimized for engineering reports."""

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import Settings

logger = logging.getLogger(__name__)

_PAGES_PER_BATCH = 32

# Separators ordered for technical/engineering document structure
ENGINEERING_SEPARATORS = [
    "\n## ",
    "\n### ",
    "\n#### ",
    "\n\n",
    "\n",
    ". ",
    "; ",
    ", ",
    " ",
    "",
]

_RE_CRLF = re.compile(r"\r\n?")
_RE_SPACES = re.compile(r"[ \t]+")
_RE_NEWLINES = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class TextChunk:
    """A chunk of document text with metadata."""

    chunk_id: str
    text: str
    page_number: int | None
    chunk_index: int


def _normalize_engineering_text(text: str) -> str:
    """Normalize whitespace and common engineering notation artifacts."""
    text = _RE_CRLF.sub("\n", text)
    text = _RE_SPACES.sub(" ", text)
    text = _RE_NEWLINES.sub("\n\n", text)
    return text.strip()


def _chunk_page_batch(
    pages: list[tuple[int, str]],
    chunk_size: int,
    chunk_overlap: int,
) -> list[tuple[int, str, int]]:
    """Chunk a batch of pages; returns (page_number, text, batch_order) tuples."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=ENGINEERING_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )

    results: list[tuple[int, str, int]] = []
    order = 0

    for page_number, page_text in pages:
        normalized = _normalize_engineering_text(page_text)
        for split in splitter.split_text(normalized):
            stripped = split.strip()
            if stripped:
                results.append((page_number, stripped, order))
                order += 1

    return results


class ChunkingService:
    """Split extracted PDF text into retrieval-optimized chunks."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._workers = settings.chunking_workers or max(1, (os.cpu_count() or 4) - 1)

    def chunk_document(
        self,
        document_id: str,
        pages: list[tuple[int, str]],
    ) -> list[TextChunk]:
        """
        Chunk per-page text while preserving page metadata.

        Uses parallel batch processing for large documents.

        Args:
            document_id: Parent document identifier.
            pages: List of (page_number, page_text) tuples.

        Returns:
            Ordered list of TextChunk objects.
        """
        if not pages:
            return []

        batches = [
            pages[i : i + _PAGES_PER_BATCH]
            for i in range(0, len(pages), _PAGES_PER_BATCH)
        ]

        raw_chunks: list[tuple[int, str, int]] = []

        if len(batches) <= 1 or self._workers <= 1:
            raw_chunks = _chunk_page_batch(
                pages,
                self._settings.chunk_size,
                self._settings.chunk_overlap,
            )
        else:
            with ThreadPoolExecutor(max_workers=self._workers) as pool:
                futures = [
                    pool.submit(
                        _chunk_page_batch,
                        batch,
                        self._settings.chunk_size,
                        self._settings.chunk_overlap,
                    )
                    for batch in batches
                ]
                for future in futures:
                    raw_chunks.extend(future.result())

            raw_chunks.sort(key=lambda item: (item[0], item[2]))

        chunks = [
            TextChunk(
                chunk_id=f"{document_id}_chunk_{idx}",
                text=text,
                page_number=page_number,
                chunk_index=idx,
            )
            for idx, (page_number, text, _) in enumerate(raw_chunks)
        ]

        logger.info(
            "Chunked document %s into %d chunks (size=%d, overlap=%d, workers=%d)",
            document_id,
            len(chunks),
            self._settings.chunk_size,
            self._settings.chunk_overlap,
            self._workers,
        )
        return chunks
