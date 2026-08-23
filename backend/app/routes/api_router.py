from fastapi import APIRouter
from .health import router as health_router
from .reports import router as reports_router
from .documents import router as documents_router
from .chat import router as chat_router
from .financials import router as financials_router

api_router = APIRouter(prefix="/api/v1")

# Register modular sub-routers
api_router.include_router(health_router)
api_router.include_router(documents_router)
api_router.include_router(reports_router)
api_router.include_router(chat_router)
api_router.include_router(financials_router)
