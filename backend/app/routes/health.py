from fastapi import APIRouter
from ..config import get_settings
from ..firebase.admin_client import is_firebase_initialized

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint to verify backend status."""
    settings = get_settings()
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "firebase_connected": is_firebase_initialized(),
        "llm_provider": settings.LLM_PROVIDER,
    }
