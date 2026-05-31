"""RAG benchmark endpoints."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.dependencies import get_benchmark_service
from app.models.schemas import BenchmarkDataset, BenchmarkRequest, BenchmarkResponse
from app.services.benchmark import BenchmarkService
from app.services.benchmark_framework import PLOTS_DIR, load_benchmark_dataset
from app.utils.exceptions import DocIntelError, to_http_exception

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmark", tags=["Benchmark"])

CASES_PATH = Path(__file__).resolve().parents[2] / "benchmark" / "benchmark_cases.json"


@router.get("/dataset", response_model=BenchmarkDataset)
async def get_benchmark_dataset() -> BenchmarkDataset:
    """Return benchmark case metadata (no answers)."""
    return load_benchmark_dataset(CASES_PATH)


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


@router.get("/plots/{filename}")
async def get_benchmark_plot(filename: str) -> FileResponse:
    """Serve generated benchmark plot PNGs."""
    safe = Path(filename).name
    plot_path = PLOTS_DIR / safe
    if not plot_path.is_file() or plot_path.suffix.lower() != ".png":
        raise HTTPException(status_code=404, detail="Plot not found")
    return FileResponse(plot_path, media_type="image/png")
