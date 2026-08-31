import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from .config import get_settings
from .routes.api_router import api_router
from .routes.documents import router as documents_router
from .routes.chat import router as chat_router
from .routes.conversations import router as conversations_router
from .firebase.admin_client import get_firebase_app
from .utils.logger import setup_logger

logger = setup_logger("app_main")


import gc
import tracemalloc

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    settings = get_settings()
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    current_mem, _ = tracemalloc.get_traced_memory()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in [{settings.ENVIRONMENT}] mode (Boot Memory: {current_mem/(1024*1024):.2f} MB)...")
    
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

    # CORS Middleware - strict origin matching based on ENVIRONMENT
    allow_origin_regex = r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?$" if settings.ENVIRONMENT == "development" else None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Security Response Headers Middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # GZip Response Compression for high concurrent load optimization
    from fastapi.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Global Exception Handlers — both inject CORS headers manually.
    def _cors_headers(request: Request) -> dict:
        origin = request.headers.get("origin") or "*"
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }

    from fastapi.exceptions import HTTPException as FastAPIHTTPException
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTP {exc.status_code} at {request.url.path}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": str(exc.detail), "error": str(exc.detail)},
            headers=_cors_headers(request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error at {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"success": False, "message": "Request validation failed.", "error": str(exc.errors())},
            headers=_cors_headers(request),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled Exception at {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An internal server error occurred.",
                "error": str(exc) if settings.DEBUG else "Internal Server Error"
            },
            headers=_cors_headers(request),
        )

    # Mount API routes
    app.include_router(api_router)
    # Also mount direct /api routes for /api/documents, /api/chat, /api/conversations
    app.include_router(documents_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(conversations_router, prefix="/api")

    # Root redirect / status
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "message": "AI Financial Report Analyzer Backend API is running.",
            "docs": "/docs",
            "version": settings.APP_VERSION
        }

    @app.get("/health", tags=["Root"])
    @app.get("/api/v1/health", tags=["Root"])
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT
        }

    return app


app = create_app()
