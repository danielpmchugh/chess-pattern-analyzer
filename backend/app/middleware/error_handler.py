"""
Global error handler middleware for Chess Pattern Analyzer API.

This middleware catches all exceptions and converts them into
structured JSON responses with proper HTTP status codes.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Union
import traceback

from app.core.exceptions import ChessAnalyzerException
from app.config import settings

logger = logging.getLogger(__name__)


async def chess_analyzer_exception_handler(
    request: Request, exc: ChessAnalyzerException
) -> JSONResponse:
    """
    Handle application-specific exceptions.

    Args:
        request: The incoming request
        exc: The ChessAnalyzerException that was raised

    Returns:
        JSONResponse with error details
    """
    logger.error(
        f"Application error: {exc.message}",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "details": exc.details,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
        },
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions from FastAPI/Starlette.

    Args:
        request: The incoming request
        exc: The HTTP exception that was raised

    Returns:
        JSONResponse with error details
    """
    logger.error(
        f"HTTP error: {exc.detail}",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: The incoming request
        exc: The validation error that was raised

    Returns:
        JSONResponse with validation error details
    """
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Format validation errors for better readability
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": {"validation_errors": errors},
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: The incoming request
        exc: The exception that was raised

    Returns:
        JSONResponse with generic error message
    """
    # Log the full traceback for debugging
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
        exc_info=True,
    )

    # In production, don't expose internal error details
    error_message = (
        str(exc) if settings.ENABLE_DETAILED_ERRORS else "An unexpected error occurred"
    )

    response_content = {
        "error": error_message,
        "request_id": getattr(request.state, "request_id", None),
        "path": request.url.path,
    }

    # Include stack trace in development mode
    if settings.DEBUG and settings.ENABLE_DETAILED_ERRORS:
        response_content["traceback"] = traceback.format_exc().split("\n")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response_content
    )
