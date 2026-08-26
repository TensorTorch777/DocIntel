"""Tests for multimodal kind detection and extraction fallbacks."""

import io
import wave
from pathlib import Path

import pytest

from app.services.media import detect_media_kind, extract_audio, extract_image
from app.utils.exceptions import MediaParseError


def _tiny_png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(32, 64, 128)).save(buf, format="PNG")
    return buf.getvalue()


def _silent_wav(path: Path, seconds: float = 0.2) -> None:
    rate = 16000
    frames = int(rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)


class TestDetectMediaKind:
    def test_pdf_by_extension(self):
        assert detect_media_kind("manual.pdf") == "pdf"

    def test_image_by_extension(self):
        assert detect_media_kind("diagram.png") == "image"

    def test_audio_by_mime_beats_webm_video_suffix(self):
        assert detect_media_kind("voice-note.webm", "audio/webm") == "audio"

    def test_video_mp4(self):
        assert detect_media_kind("clip.mp4", "video/mp4") == "video"

    def test_rejects_unknown(self):
        with pytest.raises(MediaParseError):
            detect_media_kind("notes.docx")


class TestExtractFallbacks:
    def test_image_indexes_caption_without_ocr(self, tmp_path: Path):
        path = tmp_path / "shot.png"
        path.write_bytes(_tiny_png())
        result = extract_image(path)
        assert result.kind == "image"
        assert result.page_count == 1
        assert "shot.png" in result.full_text
        assert "8×8" in result.full_text or "8x8" in result.full_text.lower()

    def test_wav_indexes_duration_without_whisper(self, tmp_path: Path):
        path = tmp_path / "note.wav"
        _silent_wav(path)
        result = extract_audio(path)
        assert result.kind == "audio"
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0.1
        assert "VOICE NOTE" in result.full_text
