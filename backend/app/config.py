"""
Configuration management for Chess Pattern Analyzer API.

This module provides environment-based configuration using Pydantic Settings.
Optimized for Railway deployment with Neon PostgreSQL and Upstash Redis.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache
import secrets


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Chess Pattern Analyzer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # API
    API_PREFIX: str = "/api/v1"
    API_TIMEOUT: int = 25  # Reduced for serverless constraints

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS - Allow frontend origins
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    ALLOWED_HOSTS: List[str] = []

    # Database - Neon PostgreSQL connection
    DATABASE_URL: Optional[str] = None
    DATABASE_POOL_SIZE: int = 5  # Neon free tier limit
    DATABASE_MAX_OVERFLOW: int = 2
    DATABASE_POOL_RECYCLE: int = 3600  # 1 hour
    DATABASE_POOL_PRE_PING: bool = True
    DATABASE_ECHO: bool = False

    # Redis - Upstash Redis connection
    REDIS_URL: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 5
    REDIS_DECODE_RESPONSES: bool = True
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5

    # Chess.com API
    CHESS_COM_API_BASE_URL: str = "https://api.chess.com/pub"
    CHESS_COM_API_TIMEOUT: int = 10
    CHESS_COM_RATE_LIMIT: int = 100  # requests per minute

    # Stockfish Engine
    STOCKFISH_PATH: str = "/usr/local/bin/stockfish"
    STOCKFISH_DEPTH: int = 18
    STOCKFISH_THREADS: int = 2
    STOCKFISH_HASH: int = 128  # MB
    STOCKFISH_TIMEOUT: int = 5  # seconds per position

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_TIER_ANONYMOUS: int = 20  # requests per hour
    RATE_LIMIT_TIER_FREE: int = 100  # requests per hour
    RATE_LIMIT_TIER_PRO: int = 1000  # requests per hour

    # Session Management
    SESSION_TTL_HOURS: int = 24
    MAX_SESSIONS: int = 1000

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Caching Strategy
    CACHE_ENABLED: bool = True
    CACHE_TTL_GAMES: int = 3600  # 1 hour for game data
    CACHE_TTL_ANALYSIS: int = 86400  # 24 hours for analysis results
    CACHE_TTL_USER_PROFILE: int = 1800  # 30 minutes for user profiles

    # Monitoring
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # Railway specific
    RAILWAY_ENVIRONMENT: Optional[str] = None
    RAILWAY_PROJECT_ID: Optional[str] = None
    RAILWAY_SERVICE_ID: Optional[str] = None

    # Feature flags
    ENABLE_SWAGGER_UI: bool = True
    ENABLE_METRICS: bool = True
    ENABLE_DETAILED_ERRORS: bool = False  # Set to False in production

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_database_url(self) -> str:
        """Get database URL with fallback for local development."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return "postgresql://postgres:postgres@localhost:5432/chess_analyzer"

    def get_redis_url(self) -> str:
        """Get Redis URL with fallback for local development."""
        if self.REDIS_URL:
            return self.REDIS_URL
        return "redis://localhost:6379/0"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once
    and reused throughout the application lifecycle.
    """
    return Settings()


# Global settings instance
settings = get_settings()
