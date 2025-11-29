"""
Health check endpoints for Chess Pattern Analyzer API.

Provides liveness, readiness, and detailed health check endpoints
for monitoring and orchestration systems (Railway, Kubernetes, etc.).
"""

from fastapi import APIRouter, Depends, status
from typing import Dict, Any
import logging
import os
import asyncio
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.

    Returns:
        Basic health status information

    Example:
        GET /api/v1/health
        Response: {"status": "healthy", "service": "chess-pattern-analyzer", ...}
    """
    return {
        "status": "healthy",
        "service": "chess-pattern-analyzer",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_probe() -> Dict[str, str]:
    """
    Kubernetes/Railway liveness probe.

    Simple endpoint that returns 200 if the application is running.
    Used to determine if the container should be restarted.

    Returns:
        Minimal liveness status

    Example:
        GET /api/v1/health/live
        Response: {"status": "alive"}
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_probe() -> Dict[str, Any]:
    """
    Kubernetes/Railway readiness probe.

    Checks if the application is ready to serve traffic by verifying:
    - Redis connection (if configured)
    - Stockfish availability (if configured)
    - Database connection (if configured)

    Returns:
        Detailed readiness status with component checks

    Example:
        GET /api/v1/health/ready
        Response: {
            "status": "ready",
            "checks": {
                "api": "ready",
                "redis": "ready",
                "stockfish": "ready"
            }
        }
    """
    checks = {
        "api": "ready",
        "redis": "unknown",
        "stockfish": "unknown",
        "database": "unknown",
    }

    # Check Redis connection
    if settings.REDIS_URL:
        try:
            from redis import asyncio as aioredis

            redis_client = aioredis.from_url(
                settings.get_redis_url(),
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2,
            )
            await asyncio.wait_for(redis_client.ping(), timeout=2.0)
            checks["redis"] = "ready"
            await redis_client.close()
        except asyncio.TimeoutError:
            logger.warning("Redis health check timed out")
            checks["redis"] = "timeout"
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            checks["redis"] = "not_ready"
    else:
        checks["redis"] = "not_configured"

    # Check Stockfish binary
    try:
        if os.path.exists(settings.STOCKFISH_PATH):
            # Verify it's executable
            if os.access(settings.STOCKFISH_PATH, os.X_OK):
                checks["stockfish"] = "ready"
            else:
                checks["stockfish"] = "not_executable"
        else:
            checks["stockfish"] = "not_found"
    except Exception as e:
        logger.warning(f"Stockfish health check failed: {e}")
        checks["stockfish"] = "error"

    # Check database connection (basic check)
    if settings.DATABASE_URL:
        try:
            # We'll implement actual DB check once we have the database setup
            # For now, just mark as configured
            checks["database"] = "configured"
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            checks["database"] = "not_ready"
    else:
        checks["database"] = "not_configured"

    # Determine overall status
    # API must be ready, other components can be not_configured
    critical_checks = ["api"]
    optional_checks = ["redis", "stockfish", "database"]

    # All critical checks must be ready
    critical_ready = all(
        checks.get(check) == "ready" for check in critical_checks
    )

    # Optional checks are okay if not_configured or ready
    optional_ready = all(
        checks.get(check) in ["ready", "not_configured", "configured"]
        for check in optional_checks
    )

    overall_status = "ready" if (critical_ready and optional_ready) else "not_ready"

    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def metrics() -> Dict[str, Any]:
    """
    Application metrics endpoint.

    Provides basic metrics for monitoring. In a full implementation,
    this would integrate with Prometheus or similar monitoring systems.

    Returns:
        Application metrics

    Example:
        GET /api/v1/health/metrics
        Response: {
            "requests_total": 1234,
            "requests_per_second": 5.2,
            ...
        }
    """
    # TODO: Implement actual metrics collection
    # This is a placeholder that will be enhanced in future tasks

    return {
        "uptime_seconds": 0,  # TODO: Track actual uptime
        "requests_total": 0,  # TODO: Implement request counter
        "requests_per_second": 0.0,  # TODO: Calculate from request counter
        "average_response_time_ms": 0.0,  # TODO: Track response times
        "active_sessions": 0,  # TODO: Track session count
        "analyses_completed": 0,  # TODO: Track analysis completions
        "cache_hit_rate": 0.0,  # TODO: Track cache performance
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/info", status_code=status.HTTP_200_OK)
async def system_info() -> Dict[str, Any]:
    """
    System information endpoint.

    Provides detailed information about the running system.
    Useful for debugging and operational visibility.

    Returns:
        System information and configuration

    Example:
        GET /api/v1/health/info
    """
    return {
        "service": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
        "configuration": {
            "debug_mode": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
            "rate_limiting_enabled": settings.RATE_LIMIT_ENABLED,
            "cache_enabled": settings.CACHE_ENABLED,
        },
        "deployment": {
            "railway_environment": settings.RAILWAY_ENVIRONMENT,
            "railway_project_id": settings.RAILWAY_PROJECT_ID,
            "railway_service_id": settings.RAILWAY_SERVICE_ID,
        },
        "integrations": {
            "chess_com_api": settings.CHESS_COM_API_BASE_URL,
            "stockfish_path": settings.STOCKFISH_PATH,
            "redis_configured": bool(settings.REDIS_URL),
            "database_configured": bool(settings.DATABASE_URL),
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
