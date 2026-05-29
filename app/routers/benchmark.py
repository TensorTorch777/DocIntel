"""RAG benchmark endpoints."""

import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_benchmark_service
from app.models.schemas import BenchmarkRequest, BenchmarkResponse
from app.services.benchmark import BenchmarkService
from app.utils.exceptions import DocIntelError, to_http_exception

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmark", tags=["Benchmark"])


@router.post("/run", response_model=BenchmarkResponse)
async def run_benchmark(
    request: BenchmarkRequest,
    benchmark: BenchmarkService = Depends(get_benchmark_service),
) -> BenchmarkResponse:
    """Run benchmark cases and return retrieval/grounding metrics."""
    try:
        return await benchmark.run(request)
    except DocIntelError as exc:
        raise to_http_exception(exc) from exc
    except Exception as exc:
        logger.exception("Benchmark failed")
        raise to_http_exception(DocIntelError(f"Benchmark failed: {exc}")) from exc
