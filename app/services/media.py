"""Multimodal extraction: PDF, images, audio (voice notes), and video.

Every modality is reduced to ordered (page/frame, text) pairs so the existing
chunk → embed → BM25/vector pipeline stays unchanged. Optional binaries
(Tesseract, ffmpeg, Whisper) improve quality; fallbacks always produce at
least a metadata caption so indexing never fails.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.services.pdf_extractor import ExtractedDocument, PageText, PDFExtractor
from app.services.transcription import with_temp_wav
from app.utils.exceptions import MediaParseError

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".bmp"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".webm"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
PDF_EXTENSIONS = {".pdf"}

IMAGE_MIMES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
    "image/tiff",
    "image/bmp",
}
AUDIO_MIMES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/aac",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
    "audio/x-m4a",
}
VIDEO_MIMES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
    "video/x-msvideo",
}


@dataclass(frozen=True)
class ExtractedMedia:
    """Unified extraction result for any supported upload."""

    kind: str
    pages: list[PageText]
    page_count: int
    full_text: str
    duration_seconds: float | None = None
    transcript_available: bool = False
    ocr_available: bool = False
    engine: str = "none"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_extracted_document(self) -> ExtractedDocument:
        return ExtractedDocument(
            pages=self.pages,
            page_count=self.page_count,
            full_text=self.full_text,
        )


def detect_media_kind(
    filename: str,
    content_type: str | None = None,
) -> str:
    """Return pdf | image | audio | video from name and optional MIME type."""
    suffix = Path(filename or "").suffix.lower()
    mime = (content_type or "").split(";")[0].strip().lower()

    if suffix in PDF_EXTENSIONS or mime == "application/pdf":
        return "pdf"
    if suffix in IMAGE_EXTENSIONS or mime in IMAGE_MIMES:
        return "image"
    if suffix in VIDEO_EXTENSIONS or mime in VIDEO_MIMES:
        # .webm is both audio and video — prefer MIME when present
        if mime in AUDIO_MIMES and mime not in VIDEO_MIMES:
            return "audio"
        if mime.startswith("audio/"):
            return "audio"
        return "video"
    if suffix in AUDIO_EXTENSIONS or mime in AUDIO_MIMES or mime.startswith("audio/"):
        return "audio"
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    raise MediaParseError(
        f"Unsupported file type '{filename or mime or 'unknown'}'. "
        "Upload a PDF, image, audio voice note, or video."
    )


def _ocr_image_bytes(data: bytes, filename: str) -> tuple[str, bool, str]:
    """Best-effort OCR. Returns (text, ocr_ran, engine)."""
    # PyMuPDF can open many image formats and optionally OCR via Tesseract.
    try:
        import fitz

        doc = fitz.open(stream=data, filetype=Path(filename).suffix.lstrip(".") or "png")
        try:
            page = doc[0]
            native = page.get_text("text").strip()
            if native:
                return native, True, "pymupdf"
            try:
                textpage = page.get_textpage_ocr(language="eng", dpi=150)
                ocr_text = page.get_text(textpage=textpage).strip()
                if ocr_text:
                    return ocr_text, True, "pymupdf-ocr"
            except Exception:
                pass
        finally:
            doc.close()
    except Exception:
        logger.debug("PyMuPDF image open failed for %s", filename, exc_info=True)

    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(image).strip()
        if text:
            return text, True, "tesseract"
    except Exception:
        logger.debug("Tesseract OCR unavailable for %s", filename, exc_info=True)

    return "", False, "none"


def _image_caption(data: bytes, filename: str) -> str:
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        width, height = image.size
        fmt = image.format or Path(filename).suffix.lstrip(".").upper() or "IMAGE"
        mode = image.mode
        return (
            f"[IMAGE] {filename}\n"
            f"Dimensions: {width}×{height}\n"
            f"Format: {fmt}\n"
            f"Color mode: {mode}"
        )
    except Exception:
        return f"[IMAGE] {filename}\n(Unable to read image metadata)"


def extract_image(path: Path, data: bytes | None = None) -> ExtractedMedia:
    payload = data if data is not None else path.read_bytes()
    ocr_text, ocr_ok, engine = _ocr_image_bytes(payload, path.name)
    caption = _image_caption(payload, path.name)
    body = caption
    notes: list[str] = []
    if ocr_text:
        body = f"{caption}\n\nOCR transcript:\n{ocr_text}"
    else:
        notes.append("No OCR text extracted; indexed image metadata for retrieval.")
        body = (
            f"{caption}\n\n"
            "No machine-readable text was extracted. Ask about the image filename "
            "or re-upload after installing Tesseract for OCR."
        )
    pages = [PageText(page_number=1, text=body)]
    return ExtractedMedia(
        kind="image",
        pages=pages,
        page_count=1,
        full_text=body,
        ocr_available=ocr_ok and bool(ocr_text),
        engine=engine,
        notes=tuple(notes),
    )


def extract_audio(path: Path) -> ExtractedMedia:
    result = with_temp_wav(path)
    notes: list[str] = []
    duration = result.duration_seconds
    if result.available and result.text:
        body = (
            f"[VOICE NOTE] {path.name}\n"
            f"Duration: {duration if duration is not None else 'unknown'} s\n"
            f"Engine: {result.engine}\n\n"
            f"Transcript:\n{result.text}"
        )
    else:
        notes.append("Speech-to-text backend unavailable; indexed audio metadata.")
        dur_line = f"{duration} s" if duration is not None else "unknown"
        body = (
            f"[VOICE NOTE] {path.name}\n"
            f"Duration: {dur_line}\n"
            "Transcript unavailable. Configure Whisper or an STT backend, "
            "or type the question after attaching this note."
        )
    pages = [PageText(page_number=1, text=body)]
    return ExtractedMedia(
        kind="audio",
        pages=pages,
        page_count=1,
        full_text=body,
        duration_seconds=duration,
        transcript_available=bool(result.available and result.text),
        engine=result.engine,
        notes=tuple(notes),
    )


def extract_video(path: Path) -> ExtractedMedia:
    from app.services.transcription import extract_keyframes

    pages: list[PageText] = []
    notes: list[str] = []
    ocr_any = False
    engine = "ffmpeg"

    audio = with_temp_wav(path)
    if audio.available and audio.text:
        pages.append(
            PageText(
                page_number=1,
                text=(
                    f"[VIDEO AUDIO] {path.name}\n"
                    f"Engine: {audio.engine}\n\n"
                    f"Soundtrack transcript:\n{audio.text}"
                ),
            )
        )
    else:
        notes.append("Video soundtrack could not be transcribed.")

    import tempfile

    with tempfile.TemporaryDirectory(prefix="docintel-frames-") as tmp:
        frames = extract_keyframes(path, Path(tmp), max_frames=8)
        if not frames:
            notes.append("ffmpeg keyframes unavailable; indexed video metadata only.")
            engine = "unavailable"
        for idx, frame in enumerate(frames, start=1):
            media = extract_image(frame)
            ocr_any = ocr_any or media.ocr_available
            pages.append(
                PageText(
                    page_number=len(pages) + 1,
                    text=f"[VIDEO FRAME {idx}] {path.name}\n{media.full_text}",
                )
            )

    if not pages:
        pages = [
            PageText(
                page_number=1,
                text=(
                    f"[VIDEO] {path.name}\n"
                    "No frames or soundtrack could be extracted. Install ffmpeg "
                    "and Whisper for full video indexing."
                ),
            )
        ]

    full_text = "\n\n".join(p.text for p in pages)
    return ExtractedMedia(
        kind="video",
        pages=pages,
        page_count=len(pages),
        full_text=full_text,
        duration_seconds=audio.duration_seconds,
        transcript_available=bool(audio.available and audio.text),
        ocr_available=ocr_any,
        engine=engine,
        notes=tuple(notes),
    )


class MediaExtractor:
    """Dispatch extraction by detected media kind."""

    def __init__(self, pdf_extractor: PDFExtractor | None = None) -> None:
        self._pdf = pdf_extractor or PDFExtractor()

    def extract(
        self,
        path: Path,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        file_bytes: bytes | None = None,
    ) -> ExtractedMedia:
        name = filename or path.name
        kind = detect_media_kind(name, content_type)
        if kind == "pdf":
            doc = self._pdf.extract(path)
            return ExtractedMedia(
                kind="pdf",
                pages=doc.pages,
                page_count=doc.page_count,
                full_text=doc.full_text,
                engine="pymupdf",
            )
        if kind == "image":
            return extract_image(path, data=file_bytes)
        if kind == "audio":
            return extract_audio(path)
        if kind == "video":
            return extract_video(path)
        raise MediaParseError(f"Unsupported media kind '{kind}'")
