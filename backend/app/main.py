"""
Main FastAPI application for Chess Pattern Analyzer API.

This module initializes the FastAPI app with all middleware,
exception handlers, and routes. Optimized for Railway deployment.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import ChessAnalyzerException
from app.middleware import (
    chess_analyzer_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    LoggingMiddleware,
)
from app.api.v1 import router as api_v1_router

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.

    Handles startup and shutdown events for the FastAPI application.
    - Startup: Initialize services, connections, etc.
    - Shutdown: Clean up resources, close connections, etc.
    """
    # Startup
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION}",
        extra={
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
        },
    )

    # Initialize services
    # TODO: Add service initialization in future tasks:
    # - Database connection pool
    # - Redis connection
    # - Stockfish engine initialization
    logger.info("Services initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down Chess Pattern Analyzer API")

    # Cleanup services
    # TODO: Add cleanup in future tasks:
    # - Close database connections
    # - Close Redis connection
    # - Cleanup Stockfish processes
    logger.info("Cleanup completed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Analyze chess games from Chess.com to identify patterns, weaknesses, and improvement opportunities",
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.ENABLE_SWAGGER_UI else None,
    redoc_url="/api/redoc" if settings.ENABLE_SWAGGER_UI else None,
    openapi_url="/api/openapi.json" if settings.ENABLE_SWAGGER_UI else None,
    lifespan=lifespan,
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# CORS configuration - must be added before other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# Trusted host middleware for security (only in production)
if settings.is_production() and settings.ALLOWED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

# Register exception handlers
app.add_exception_handler(ChessAnalyzerException, chess_analyzer_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API routers
app.include_router(
    api_v1_router,
    prefix=settings.API_PREFIX,
)


# Root endpoint
@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict:
    """
    Root endpoint providing API information.

    Returns:
        Basic API information and links to documentation
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "documentation": {
            "swagger": "/api/docs" if settings.ENABLE_SWAGGER_UI else None,
            "redoc": "/api/redoc" if settings.ENABLE_SWAGGER_UI else None,
        },
        "endpoints": {
            "health": f"{settings.API_PREFIX}/health",
            "health_ready": f"{settings.API_PREFIX}/health/ready",
            "health_live": f"{settings.API_PREFIX}/health/live",
        },
    }


# Additional utility endpoint for Railway
@app.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz() -> dict:
    """
    Railway-specific health check endpoint.

    Railway looks for /healthz by default, so we provide
    a simple endpoint here that redirects to our health check.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
