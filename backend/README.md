# Chess Pattern Analyzer API

FastAPI backend service for analyzing chess games from Chess.com to identify patterns, weaknesses, and improvement opportunities.

## Features

- **FastAPI Framework**: High-performance async API with automatic OpenAPI documentation
- **Health Monitoring**: Comprehensive health check endpoints for Railway deployment
- **Error Handling**: Global error handler with structured error responses
- **Logging**: JSON structured logging for production, colored output for development
- **CORS Support**: Configurable CORS for frontend integration
- **Rate Limiting**: Built-in rate limiting support (to be implemented)
- **Caching**: Redis-based caching strategy for optimal performance
- **Docker Ready**: Optimized Dockerfile for Railway deployment

## Tech Stack

- **Framework**: FastAPI 0.109+
- **Python**: 3.11+
- **Database**: PostgreSQL (via Neon)
- **Cache**: Redis (via Upstash)
- **Chess Engine**: Stockfish 16
- **Deployment**: Railway (Docker-based)

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Settings and configuration
│   ├── api/
│   │   └── v1/
│   │       ├── router.py    # API router aggregation
│   │       └── health.py    # Health check endpoints
│   ├── core/
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── logging.py       # Logging configuration
│   ├── middleware/
│   │   ├── error_handler.py # Error handling middleware
│   │   └── logging.py       # Request logging middleware
│   ├── models/              # Data models (to be added)
│   ├── services/            # Business logic services (to be added)
│   └── tests/
│       ├── conftest.py      # Pytest fixtures
│       ├── test_config.py   # Configuration tests
│       ├── test_exceptions.py # Exception tests
│       └── test_health.py   # Health endpoint tests
├── Dockerfile               # Production Docker image
├── docker-compose.yml       # Local development setup
├── requirements.txt         # Python dependencies
├── pytest.ini              # Pytest configuration
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for local development)
- PostgreSQL (or use Docker Compose)
- Redis (or use Docker Compose)

### Local Development with Docker Compose

1. **Clone the repository**:
   ```bash
   cd chess/backend
   ```

2. **Copy environment variables**:
   ```bash
   cp .env.example .env
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

   This starts:
   - PostgreSQL database on port 5432
   - Redis cache on port 6379
   - FastAPI backend on port 8000

4. **Check health**:
   ```bash
   curl http://localhost:8000/healthz
   ```

5. **View API documentation**:
   Open http://localhost:8000/api/docs in your browser

### Local Development without Docker

1. **Create virtual environment**:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

4. **Run the application**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the API**:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/api/docs
   - Health: http://localhost:8000/api/v1/health

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest app/tests/test_health.py

# Run with verbose output
pytest -v

# Run only unit tests
pytest -m unit
```

## API Endpoints

### Root & Documentation
- `GET /` - API information
- `GET /api/docs` - Swagger UI documentation
- `GET /api/redoc` - ReDoc documentation
- `GET /api/openapi.json` - OpenAPI schema

### Health Checks
- `GET /healthz` - Railway health check
- `GET /api/v1/health` - Basic health status
- `GET /api/v1/health/live` - Liveness probe
- `GET /api/v1/health/ready` - Readiness probe (checks dependencies)
- `GET /api/v1/health/metrics` - Application metrics
- `GET /api/v1/health/info` - System information

## Configuration

All configuration is managed through environment variables. See `.env.example` for all available options.

### Key Configuration Variables

- `ENVIRONMENT`: Environment (development, staging, production)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `CORS_ORIGINS`: Allowed frontend origins (JSON array)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `SECRET_KEY`: Secret key for JWT tokens (generate securely!)

### Railway Deployment

Railway automatically detects the Dockerfile and deploys the application.

1. **Connect your repository to Railway**
2. **Set environment variables** in Railway dashboard:
   - `DATABASE_URL` (from Neon)
   - `REDIS_URL` (from Upstash)
   - `ENVIRONMENT=production`
   - `SECRET_KEY` (generate securely)
   - `CORS_ORIGINS` (your frontend URL)

3. **Deploy**:
   Railway will automatically build and deploy on git push.

### Environment Variables for Railway

```bash
# Production settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database (from Neon)
DATABASE_URL=postgresql://user:password@host/database

# Redis (from Upstash)
REDIS_URL=rediss://default:xxx@host:6379

# CORS (your frontend domain)
CORS_ORIGINS=["https://your-app.vercel.app"]

# Security
SECRET_KEY=your-secure-secret-key-here
```

## Development Workflow

1. Create a new branch for your feature
2. Write tests first (TDD approach)
3. Implement the feature
4. Ensure tests pass: `pytest`
5. Check code quality: `ruff check .`
6. Format code: `black .`
7. Commit and push
8. Create pull request

## Code Quality

### Linting
```bash
ruff check app/
```

### Formatting
```bash
black app/
```

### Type Checking
```bash
mypy app/
```

## Architecture Decisions

### Railway Optimization
- **Multi-stage Docker build**: Reduces final image size
- **Non-root user**: Security best practice
- **Health checks**: Built into Dockerfile for container orchestration
- **Port flexibility**: Uses Railway's PORT environment variable

### Serverless Constraints
- **25-second timeout**: Analysis operations optimized for quick completion
- **512MB RAM**: Efficient memory usage with connection pooling
- **Connection limits**: Database pool size limited to 5 (Neon free tier)
- **Redis commands**: Caching strategy optimized for 10k commands/day

### Performance Optimizations
- **Async everywhere**: All I/O operations are async for maximum concurrency
- **Connection pooling**: Efficient database and Redis connection management
- **Multi-layer caching**: Memory → Redis → Database
- **JSON logging**: Structured logs for production monitoring

## Contributing

1. Follow PEP 8 style guidelines
2. Write comprehensive docstrings
3. Maintain 80%+ test coverage
4. Use type hints everywhere
5. Update tests for new features
6. Document configuration changes

## License

Internal project - All rights reserved

## Support

For issues or questions, contact the technical lead or create an issue in the repository.
