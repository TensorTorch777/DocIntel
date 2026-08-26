"""Custom exception hierarchy for DocIntel."""

from fastapi import HTTPException, status


class DocIntelError(Exception):
    """Base exception for DocIntel domain errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EmptyDocumentError(DocIntelError):
    """Raised when a PDF contains no extractable text."""


class PDFParseError(DocIntelError):
    """Raised when PDF parsing fails."""


class MediaParseError(DocIntelError):
    """Raised when image, audio, or video parsing fails."""


class DocumentNotFoundError(DocIntelError):
    """Raised when a document ID is not found in the vector store."""


class LLMTimeoutError(DocIntelError):
    """Raised when the LLM request exceeds the configured timeout."""


def to_http_exception(exc: DocIntelError) -> HTTPException:
    """Map domain exceptions to HTTP responses."""
    status_map: dict[type[DocIntelError], int] = {
        EmptyDocumentError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        PDFParseError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        MediaParseError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        DocumentNotFoundError: status.HTTP_404_NOT_FOUND,
        LLMTimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
    }
    code = status_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    return HTTPException(status_code=code, detail=exc.message)
