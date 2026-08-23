import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from .config import get_settings
from .routes.api_router import api_router
from .routes.documents import router as documents_router
from .firebase.admin_client import get_firebase_app
from .utils.logger import setup_logger

logger = setup_logger("app_main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in [{settings.ENVIRONMENT}] mode...")
    
    # Initialize Firebase Admin SDK if credentials exist
    get_firebase_app()
    
    # Ensure local upload directory exists
    os.makedirs(os.path.join(os.getcwd(), "uploads"), exist_ok=True)
    
    yield
    
    logger.info("Shutting down application...")


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Production-grade AI Financial Report Analyzer using Retrieval-Augmented Generation (RAG).",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled Exception at {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An internal server error occurred.",
                "error": str(exc) if settings.DEBUG else "Internal Server Error"
            }
        )

    # Mount API routes
    app.include_router(api_router)
    # Also mount documents router directly under /api for /api/documents/upload
    app.include_router(documents_router, prefix="/api")

    # Static files for local uploads
    upload_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

    # Root redirect / status
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "message": "AI Financial Report Analyzer Backend API is running.",
            "docs": "/docs",
            "version": settings.APP_VERSION
        }

    return app


app = create_app()
