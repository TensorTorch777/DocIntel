"""PDF text extraction using PyMuPDF."""

import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import fitz

from app.utils.exceptions import EmptyDocumentError, PDFParseError

logger = logging.getLogger(__name__)

_PAGES_PER_WORKER = 64


@dataclass(frozen=True)
class PageText:
    """Text content extracted from a single PDF page."""

    page_number: int
    text: str


@dataclass(frozen=True)
class ExtractedDocument:
    """Full extraction result from a PDF."""

    pages: list[PageText]
    page_count: int
    full_text: str


def _extract_page_range(file_path: str, start: int, end: int) -> list[PageText]:
    """Extract text from a page range (runs in a worker process)."""
    doc = fitz.open(file_path)
    pages: list[PageText] = []
    try:
        for idx in range(start, min(end, len(doc))):
            text = doc.load_page(idx).get_text("text").strip()
            if text:
                pages.append(PageText(page_number=idx + 1, text=text))
    finally:
        doc.close()
    return pages


class PDFExtractor:
    """Extract text from PDF files efficiently with PyMuPDF."""

    def __init__(self, workers: int = 0) -> None:
        self._workers = workers or max(1, (os.cpu_count() or 4) - 1)

    def extract(self, file_path: Path) -> ExtractedDocument:
        """
        Extract text from every page of a PDF.

        Uses parallel workers for large documents.

        Args:
            file_path: Path to the PDF on disk.

        Returns:
            ExtractedDocument with per-page and concatenated text.

        Raises:
            PDFParseError: If the file cannot be opened or parsed.
            EmptyDocumentError: If no text could be extracted.
        """
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()
        except Exception as exc:
            logger.exception("Failed to open PDF: %s", file_path)
            raise PDFParseError(f"Failed to parse PDF: {exc}") from exc

        path_str = str(file_path)
        ranges = [
            (start, start + _PAGES_PER_WORKER)
            for start in range(0, page_count, _PAGES_PER_WORKER)
        ]

        pages: list[PageText] = []

        if len(ranges) <= 1 or self._workers <= 1:
            pages = _extract_page_range(path_str, 0, page_count)
        else:
            with ProcessPoolExecutor(max_workers=self._workers) as pool:
                futures = {
                    pool.submit(_extract_page_range, path_str, start, end): start
                    for start, end in ranges
                }
                for future in as_completed(futures):
                    pages.extend(future.result())

            pages.sort(key=lambda p: p.page_number)

        if not pages:
            raise EmptyDocumentError(
                "No extractable text found in PDF. "
                "The document may be scanned/image-only."
            )

        full_text = "\n\n".join(p.text for p in pages)
        logger.info(
            "Extracted %d pages with text from %d total pages (%d workers)",
            len(pages),
            page_count,
            self._workers,
        )
        return ExtractedDocument(pages=pages, page_count=page_count, full_text=full_text)
