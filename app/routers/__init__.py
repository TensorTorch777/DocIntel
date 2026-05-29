"""API route modules."""

from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.upload import router as upload_router

__all__ = ["chat_router", "documents_router", "upload_router"]
