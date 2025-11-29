# Task: BACKEND-001 - REST API Framework

**Status**: `completed`
**Priority**: Critical
**Assigned Agent**: backend-developer
**Estimated Effort**: 1 day
**Dependencies**: None

## Objective

Set up the FastAPI backend framework with proper structure, middleware, error handling, CORS configuration, and Azure Container Apps deployment readiness.

## Success Criteria

1. FastAPI application with modular structure
2. Proper middleware stack (CORS, error handling, logging)
3. Health check and monitoring endpoints
4. OpenAPI documentation auto-generated
5. Environment-based configuration
6. Docker containerization ready
7. Azure Container Apps compatible
8. Request/response validation with Pydantic

## Technical Approach

### 1. Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings and configuration
│   ├── dependencies.py      # Dependency injection
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── cors.py
│   │   ├── error_handler.py
│   │   ├── logging.py
│   │   └── rate_limit.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── analysis.py
│   │   │   ├── users.py
│   │   │   └── health.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py
│   │   ├── security.py
│   │   └── utils.py
│   ├── models/
│   │   └── ... (from DATA-001)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chess_com.py
│   │   ├── analysis.py
│   │   └── storage.py
│   └── tests/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

### 2. Main Application Setup

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.api.v1 import router as api_router
from app.middleware import (
    ErrorHandlerMiddleware,
    LoggingMiddleware,
    RequestIdMiddleware
)
from app.core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting Chess Pattern Analyzer API")

    # Initialize services
    await initialize_services()

    yield

    # Shutdown
    logger.info("Shutting down Chess Pattern Analyzer API")
    await cleanup_services()

# Create FastAPI app
app = FastAPI(
    title="Chess Pattern Analyzer API",
    description="Analyze chess games to identify weaknesses and patterns",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-RateLimit-Remaining"]
)

# Trusted host middleware for security
if settings.ALLOWED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Include API routers
app.include_router(
    api_router,
    prefix="/api/v1"
)

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "Chess Pattern Analyzer API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/api/docs"
    }
```

### 3. Configuration Management

```python
# app/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Chess Pattern Analyzer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # API
    API_PREFIX: str = "/api/v1"
    API_TIMEOUT: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ALLOWED_HOSTS: List[str] = []

    # Azure
    AZURE_REDIS_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_APP_INSIGHTS_KEY: Optional[str] = None

    # Chess.com API
    CHESS_COM_API_BASE_URL: str = "https://api.chess.com/pub"
    CHESS_COM_API_TIMEOUT: int = 10

    # Stockfish
    STOCKFISH_PATH: str = "/usr/local/bin/stockfish"
    STOCKFISH_DEPTH: int = 18
    STOCKFISH_THREADS: int = 2

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_TIER_ANONYMOUS: int = 20
    RATE_LIMIT_TIER_FREE: int = 100
    RATE_LIMIT_TIER_PRO: int = 1000

    # Session
    SESSION_TTL_HOURS: int = 24
    MAX_SESSIONS: int = 1000

    # Security
    SECRET_KEY: str = os.urandom(32).hex()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Monitoring
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

settings = get_settings()
```

### 4. Error Handling

```python
# app/core/exceptions.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ChessAnalyzerException(Exception):
    """Base exception for application"""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class UserNotFoundException(ChessAnalyzerException):
    """Chess.com user not found"""
    def __init__(self, username: str):
        super().__init__(
            message=f"Chess.com user '{username}' not found",
            status_code=404,
            details={"username": username}
        )

class RateLimitExceededException(ChessAnalyzerException):
    """Rate limit exceeded"""
    def __init__(self, reset_time: str):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            details={"reset_time": reset_time}
        )

class AnalysisFailedException(ChessAnalyzerException):
    """Game analysis failed"""
    def __init__(self, reason: str):
        super().__init__(
            message=f"Analysis failed: {reason}",
            status_code=500,
            details={"reason": reason}
        )

# app/middleware/error_handler.py
class ErrorHandlerMiddleware:
    """Global error handler middleware"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except ChessAnalyzerException as e:
            logger.error(f"Application error: {e.message}", exc_info=True)
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.message,
                    "details": e.details,
                    "request_id": request.state.request_id
                }
            )
        except HTTPException as e:
            logger.error(f"HTTP error: {e.detail}", exc_info=True)
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.detail,
                    "request_id": request.state.request_id
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "An unexpected error occurred",
                    "request_id": request.state.request_id
                }
            )
```

### 5. API Router Structure

```python
# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1 import health, analysis, users

router = APIRouter()

router.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)

router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["analysis"]
)

router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)
```

### 6. Health Check Endpoints

```python
# app/api/v1/health.py
from fastapi import APIRouter, Depends
from typing import Dict, Any
import aioredis
from app.config import settings
from app.dependencies import get_redis_client

router = APIRouter()

@router.get("/")
async def health_check() -> Dict[str, str]:
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "chess-pattern-analyzer",
        "version": settings.APP_VERSION
    }

@router.get("/live")
async def liveness_probe() -> Dict[str, str]:
    """Kubernetes liveness probe"""
    return {"status": "alive"}

@router.get("/ready")
async def readiness_probe(
    redis: aioredis.Redis = Depends(get_redis_client)
) -> Dict[str, Any]:
    """Kubernetes readiness probe"""
    checks = {
        "api": "ready",
        "redis": "unknown",
        "stockfish": "unknown"
    }

    # Check Redis
    try:
        await redis.ping()
        checks["redis"] = "ready"
    except Exception:
        checks["redis"] = "not_ready"

    # Check Stockfish
    try:
        # Verify Stockfish binary exists
        import os
        if os.path.exists(settings.STOCKFISH_PATH):
            checks["stockfish"] = "ready"
        else:
            checks["stockfish"] = "not_ready"
    except Exception:
        checks["stockfish"] = "not_ready"

    # Overall status
    all_ready = all(v == "ready" for v in checks.values())

    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks
    }

@router.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """Application metrics for monitoring"""
    return {
        "requests_total": 0,  # TODO: Implement metrics collection
        "requests_per_second": 0,
        "average_response_time": 0,
        "active_sessions": 0,
        "analyses_completed": 0
    }
```

### 7. Logging Configuration

```python
# app/core/logging.py
import logging
import sys
from app.config import settings
import json

class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""

    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if hasattr(record, 'request_id'):
            log_obj['request_id'] = record.request_id

        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_obj)

def setup_logging():
    """Configure application logging"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper())

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)

    if settings.ENVIRONMENT == "production":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )

    root_logger.addHandler(console_handler)

    # Reduce noise from libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
```

### 8. Dockerfile for Azure Container Apps

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Stockfish
RUN wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-ubuntu-x64-avx2.tar \
    && tar -xf stockfish-ubuntu-x64-avx2.tar \
    && mv stockfish/stockfish-ubuntu-x64-avx2 /usr/local/bin/stockfish \
    && rm -rf stockfish*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health/live')"

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 9. Requirements File

```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
httpx==0.25.1
aioredis==2.0.1
python-chess==1.999
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
slowapi==0.1.9
prometheus-client==0.19.0
sentry-sdk==1.38.0
pytest==7.4.3
pytest-asyncio==0.21.1
```

## Implementation Steps

1. Create project structure
2. Set up FastAPI application
3. Implement configuration management
4. Add middleware stack
5. Create error handling system
6. Set up logging framework
7. Implement health check endpoints
8. Create Docker configuration
9. Add API documentation
10. Write integration tests

## Testing Requirements

### Unit Tests
- Test configuration loading
- Test error handlers
- Test middleware functionality
- Test health endpoints
- Test logging output

### Integration Tests
- Test full API startup
- Test middleware chain
- Test error propagation
- Test CORS headers
- Test Docker container

## Acceptance Criteria

- [ ] FastAPI app starts successfully
- [ ] OpenAPI docs accessible at /api/docs
- [ ] Health checks return proper status
- [ ] CORS configured for frontend
- [ ] Error handling works globally
- [ ] Structured logging implemented
- [ ] Docker container builds and runs
- [ ] Azure Container Apps compatible
- [ ] 90% test coverage

## Azure Container Apps Configuration

```yaml
# azure-container-app.yaml
properties:
  managedEnvironmentId: /subscriptions/.../managedEnvironments/chess-env
  configuration:
    ingress:
      external: true
      targetPort: 8000
      transport: http
      corsPolicy:
        allowedOrigins:
          - https://chess-analyzer.azurestaticapps.net
    secrets:
      - name: redis-connection
        value: ${AZURE_REDIS_CONNECTION_STRING}
  template:
    containers:
      - name: chess-api
        image: chessanalyzer.azurecr.io/chess-api:latest
        resources:
          cpu: 0.5
          memory: 1Gi
        env:
          - name: AZURE_REDIS_CONNECTION_STRING
            secretRef: redis-connection
          - name: ENVIRONMENT
            value: production
    scale:
      minReplicas: 1
      maxReplicas: 10
      rules:
        - name: http-rule
          http:
            metadata:
              concurrentRequests: 100
```

## Notes

- FastAPI chosen for automatic OpenAPI documentation
- Structured logging essential for Azure monitoring
- Health checks required for Container Apps
- Consider adding OpenTelemetry for distributed tracing
- Rate limiting middleware will be added from API-002 task