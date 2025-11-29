"""
Request logging middleware for Chess Pattern Analyzer API.

This middleware logs all incoming requests and outgoing responses
with timing information and request IDs for tracing.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time
import uuid

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.

    Adds request ID to each request and logs:
    - Request method, path, and client IP
    - Response status code and timing
    - Request ID for distributed tracing
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and log details.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response from the handler
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract client information
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Log incoming request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": client_host,
                "user_agent": user_agent,
            },
        )

        # Process request and measure time
        start_time = time.time()

        try:
            response = await call_next(request)

            # Calculate request duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "client_host": client_host,
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Log exception
            duration = time.time() - start_time

            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "client_host": client_host,
                    "error": str(exc),
                },
                exc_info=True,
            )

            # Re-raise to be handled by error handler
            raise


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware to add request IDs.

    Alternative to LoggingMiddleware if you only need request IDs.
    """

    async def dispatch(self, request: Request, call_next):
        """Add request ID to request state."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response
