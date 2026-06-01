"""DocIntel FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.upload import router as upload_router
from app.utils.exceptions import DocIntelError, to_http_exception

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown lifecycle hooks."""
    settings = get_settings()
    settings.ensure_directories()
    logger.info(
        "DocIntel starting — LLM=%s @ %s | embeddings=%s",
        settings.llm_model,
        settings.llm_base_url,
        settings.embedding_model,
    )
    yield
    logger.info("DocIntel shutting down")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "GenAI Document Intelligence microservice for multi-hundred-page "
            "engineering reports. Upload PDFs, index with ChromaDB, and query "
            "via RAG with local Qwen2.5 inference."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        # Next.js may pick 3001+ when 3000 is busy
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(upload_router)
    app.include_router(chat_router)
    app.include_router(documents_router)

    @app.get("/health", tags=["Health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @app.exception_handler(DocIntelError)
    async def docintel_exception_handler(
        request: Request,
        exc: DocIntelError,
    ) -> JSONResponse:
        http_exc = to_http_exception(exc)
        return JSONResponse(status_code=http_exc.status_code, content={"detail": exc.message})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc) or "Internal server error"},
        )

    return app


app = create_app()
