"""End-to-end API tests for multimodal upload, analyze, and MoE chat."""

from __future__ import annotations

import io
import json
import wave
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.dependencies import (
    get_ingestion_service,
    get_media_extractor,
    get_rag_service,
    get_vector_store,
)
from app.services.bm25_store import BM25Store
from app.services.chunking import ChunkingService
from app.services.ingestion import IngestionService
from app.services.media import MediaExtractor, extract_video
from app.services.pdf_extractor import PDFExtractor
from app.services.rag import RAGService
from app.services.reranker import RerankerService
from app.services.retrieval import RetrievalService
from app.services.vector_store import VectorStoreService


class FakeEmbedding:
    device = "cpu"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.05] * 16 for _ in texts]

    def embed_query(self, query: str) -> list[float]:
        return [0.05] * 16


class FakeLLM:
    async def stream_completion(self, *args, **kwargs) -> AsyncIterator[str]:
        yield "Grounded test answer. "
        yield "[Source 1]"

    async def complete(self, *args, **kwargs) -> str:
        return "Grounded test answer. [Source 1]"


def _png_bytes(width: int = 12, height: int = 10) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(40, 80, 120)).save(buf, format="PNG")
    return buf.getvalue()


def _wav_bytes(seconds: float = 0.25) -> bytes:
    buf = io.BytesIO()
    rate = 16000
    frames = int(rate * seconds)
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.split("\n\n"):
        event = "message"
        data = ""
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            if line.startswith("data:"):
                data = line[5:].strip()
        if data:
            events.append((event, json.loads(data)))
    return events


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("CHROMA_COLLECTION_NAME", "test_multimodal_api")
    monkeypatch.setenv("RERANKER_ENABLED", "false")
    monkeypatch.setenv("ENABLE_ANSWER_VERIFICATION", "false")
    monkeypatch.setenv("ENABLE_QUERY_REWRITE_LLM", "false")

    get_settings.cache_clear()
    settings = get_settings()
    settings.ensure_directories()

    embeddings = FakeEmbedding()
    vector_store = VectorStoreService(settings)
    bm25 = BM25Store(settings)
    chunking = ChunkingService(settings)
    pdf = PDFExtractor(workers=1)
    media = MediaExtractor(pdf)
    ingestion = IngestionService(
        settings, pdf, chunking, embeddings, vector_store, bm25, media
    )
    llm = FakeLLM()
    retrieval = RetrievalService(
        settings,
        embeddings,
        vector_store,
        bm25,
        RerankerService(settings),
        llm,
    )
    rag = RAGService(settings, retrieval, llm)

    from main import create_app

    app = create_app()
    app.dependency_overrides[get_ingestion_service] = lambda: ingestion
    app.dependency_overrides[get_media_extractor] = lambda: media
    app.dependency_overrides[get_rag_service] = lambda: rag
    app.dependency_overrides[get_vector_store] = lambda: vector_store

    with TestClient(app) as client:
        yield client


class TestHealthAndRejection:
    def test_health(self, api_client: TestClient):
        res = api_client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_rejects_unsupported_type(self, api_client: TestClient):
        res = api_client.post(
            "/upload",
            files={"file": ("notes.docx", b"not a document", "application/vnd.openxmlformats")},
        )
        assert res.status_code == 400


class TestImageAndVoiceAPI:
    def test_upload_image_indexes_caption(self, api_client: TestClient):
        res = api_client.post(
            "/upload",
            files={"file": ("diagram.png", _png_bytes(), "image/png")},
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["modality"] == "image"
        assert body["chunk_count"] >= 1
        assert body["page_count"] == 1
        assert body["document_id"]

        info = api_client.get(f"/documents/{body['document_id']}")
        assert info.status_code == 200
        assert info.json()["modality"] == "image"

    def test_upload_wav_voice_note(self, api_client: TestClient):
        res = api_client.post(
            "/upload",
            files={"file": ("voice-note.wav", _wav_bytes(), "audio/wav")},
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["modality"] == "audio"
        assert body["chunk_count"] >= 1
        assert body["duration_seconds"] is not None
        assert body["duration_seconds"] >= 0.2

    def test_analyze_image_attachment(self, api_client: TestClient):
        res = api_client.post(
            "/media/analyze",
            files={"file": ("shot.png", _png_bytes(16, 9), "image/png")},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["modality"] == "image"
        assert "shot.png" in body["text"]
        assert "16" in body["text"]

    def test_analyze_voice_note(self, api_client: TestClient):
        res = api_client.post(
            "/media/analyze",
            files={"file": ("voice-note.wav", _wav_bytes(), "audio/wav")},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["modality"] == "audio"
        assert "VOICE NOTE" in body["text"]
        assert body["engine"] in {"unavailable", "whisper-tiny"}

    def test_analyze_webm_audio_mime(self, api_client: TestClient):
        # Browser voice notes often send audio/webm with a .webm suffix
        res = api_client.post(
            "/media/analyze",
            files={"file": ("voice-note.webm", _wav_bytes(), "audio/webm")},
        )
        assert res.status_code == 200, res.text
        assert res.json()["modality"] == "audio"


class TestMoEChatWithAttachment:
    def test_chat_sse_includes_moe_vision_routing(self, api_client: TestClient):
        uploaded = api_client.post(
            "/upload",
            files={"file": ("manual-shot.png", _png_bytes(), "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        doc_id = uploaded.json()["document_id"]

        res = api_client.post(
            "/chat",
            json={
                "document_id": doc_id,
                "query": "What register is shown in this screenshot?",
                "task": "qa",
                "attachment_context": (
                    "PG — Paging (bit 31 of CR0)\n"
                    "Screenshot of CR0 control register definition."
                ),
                "attachment_modality": "image",
            },
        )
        assert res.status_code == 200, res.text
        events = _parse_sse(res.text)
        kinds = [k for k, _ in events]
        assert "pipeline" in kinds
        assert "done" in kinds

        moe_events = [
            payload
            for kind, payload in events
            if kind == "pipeline" and payload.get("stage") == "moe_routing"
        ]
        assert moe_events, f"missing moe_routing in {events!r}"
        completed = moe_events[-1]
        assert completed["status"] == "completed"
        assert completed["detail"]["primary"] == "vision"
        experts = {e["expert"] for e in completed["detail"]["experts"]}
        assert "vision" in experts

        done = [p for k, p in events if k == "done"]
        assert done
        assert done[-1].get("moe", {}).get("primary") == "vision"

    def test_chat_audio_attachment_routes_audio_expert(self, api_client: TestClient):
        uploaded = api_client.post(
            "/upload",
            files={"file": ("voice-note.wav", _wav_bytes(), "audio/wav")},
        )
        assert uploaded.status_code == 201
        doc_id = uploaded.json()["document_id"]

        res = api_client.post(
            "/chat",
            json={
                "document_id": doc_id,
                "query": "Does CR3 store the faulting address?",
                "attachment_context": "[VOICE NOTE] user asked about CR3 page faults",
                "attachment_modality": "audio",
            },
        )
        assert res.status_code == 200, res.text
        events = _parse_sse(res.text)
        moe = [
            p
            for k, p in events
            if k == "pipeline" and p.get("stage") == "moe_routing" and p.get("status") == "completed"
        ]
        assert moe
        assert moe[-1]["detail"]["primary"] == "audio"


def test_video_extract_fallback_without_ffmpeg(tmp_path: Path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"not a real mp4 container")
    result = extract_video(clip)
    assert result.kind == "video"
    assert result.page_count >= 1
    assert "VIDEO" in result.full_text
    assert result.engine in {"ffmpeg", "unavailable"}
