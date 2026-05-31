"""RAG benchmark API service."""

import logging

from app.models.schemas import BenchmarkRequest, BenchmarkResponse
from app.services.benchmark_framework import BenchmarkFramework
from app.services.rag import RAGService

logger = logging.getLogger(__name__)


class BenchmarkService:
    """Run comprehensive benchmark suite via API."""

    def __init__(self, rag_service: RAGService) -> None:
        self._framework = BenchmarkFramework(rag_service)

    async def run(self, request: BenchmarkRequest) -> BenchmarkResponse:
        return await self._framework.run(request)
