"""Sentence Transformer embedding generation."""

import logging
from functools import lru_cache

import torch
from sentence_transformers import SentenceTransformer

from app.config import Settings

logger = logging.getLogger(__name__)


def _resolve_device(setting: str) -> str:
    """Pick embedding device from config, falling back to CPU if CUDA unavailable."""
    if setting == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if setting == "cuda" and not torch.cuda.is_available():
        logger.warning("EMBEDDING_DEVICE=cuda but no GPU found — falling back to CPU")
        return "cpu"
    return setting


@lru_cache(maxsize=4)
def _load_model(model_name: str, device: str) -> SentenceTransformer:
    """Load and cache the embedding model (singleton per process + device)."""
    logger.info("Loading embedding model: %s on %s", model_name, device)
    return SentenceTransformer(model_name, device=device)


class EmbeddingService:
    """Generate dense vector embeddings for text chunks."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._device = _resolve_device(settings.embedding_device)
        self._model = _load_model(settings.embedding_model, self._device)
        self._batch_size = settings.embedding_batch_size

    @property
    def device(self) -> str:
        return self._device

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts with GPU batching when available.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors as float lists.
        """
        if not texts:
            return []

        encode_kwargs: dict = {
            "normalize_embeddings": True,
            "show_progress_bar": False,
            "convert_to_numpy": True,
            "batch_size": self._batch_size,
        }

        if self._device.startswith("cuda"):
            encode_kwargs["device"] = self._device

        embeddings = self._model.encode(texts, **encode_kwargs)
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string for retrieval."""
        return self.embed_texts([query])[0]
