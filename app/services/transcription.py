"""Optional speech-to-text backends for voice notes and video soundtracks.

Whisper / ffmpeg are optional. Tests and CPU-only environments fall back to a
duration-aware stub so ingestion never hard-fails.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    duration_seconds: float | None
    engine: str
    available: bool


def wav_duration_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate() or 1
            return round(frames / float(rate), 3)
    except Exception:
        return None


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def whisper_available() -> bool:
    try:
        import whisper  # noqa: F401

        return True
    except Exception:
        return False


def transcribe_audio(path: Path) -> TranscriptResult:
    """Transcribe an audio file; never raises on missing STT backends."""
    duration = wav_duration_seconds(path) if path.suffix.lower() == ".wav" else None

    if whisper_available():
        try:
            import whisper

            model = whisper.load_model("tiny")
            result = model.transcribe(str(path))
            text = str(result.get("text") or "").strip()
            return TranscriptResult(
                text=text,
                duration_seconds=duration,
                engine="whisper-tiny",
                available=True,
            )
        except Exception:
            logger.warning("Whisper transcription failed; using fallback", exc_info=True)

    return TranscriptResult(
        text="",
        duration_seconds=duration,
        engine="unavailable",
        available=False,
    )


def extract_audio_wav(source: Path, dest: Path) -> bool:
    """Extract a 16 kHz mono WAV from video/audio via ffmpeg. Returns False if unavailable."""
    if not ffmpeg_available():
        return False
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "wav",
                str(dest),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return dest.exists() and dest.stat().st_size > 0
    except Exception:
        logger.warning("ffmpeg audio extract failed for %s", source, exc_info=True)
        return False


def extract_keyframes(source: Path, dest_dir: Path, max_frames: int = 8) -> list[Path]:
    """Extract up to ``max_frames`` JPEG keyframes. Empty list if ffmpeg missing."""
    if not ffmpeg_available():
        return []
    dest_dir.mkdir(parents=True, exist_ok=True)
    pattern = dest_dir / "frame_%03d.jpg"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-vf",
                f"fps=1,scale=min(1280\\,iw):-2",
                "-frames:v",
                str(max_frames),
                str(pattern),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return sorted(dest_dir.glob("frame_*.jpg"))
    except Exception:
        logger.warning("ffmpeg keyframe extract failed for %s", source, exc_info=True)
        return []


def with_temp_wav(source: Path) -> TranscriptResult:
    """Transcribe non-WAV audio/video by converting first when ffmpeg exists."""
    if source.suffix.lower() == ".wav":
        return transcribe_audio(source)
    with tempfile.TemporaryDirectory(prefix="docintel-stt-") as tmp:
        wav_path = Path(tmp) / "track.wav"
        if extract_audio_wav(source, wav_path):
            return transcribe_audio(wav_path)
    return TranscriptResult(text="", duration_seconds=None, engine="unavailable", available=False)
