"""
Tests for configuration management.

This module tests the Settings class and configuration loading
to ensure environment variables are properly handled.
"""

import pytest
import os
from app.config import Settings, get_settings


def test_default_settings():
    """Test that default settings are correctly loaded."""
    settings = Settings()

    assert settings.APP_NAME == "Chess Pattern Analyzer"
    assert settings.APP_VERSION == "1.0.0"
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is False
    assert settings.API_PREFIX == "/api/v1"
    assert settings.PORT == 8000


def test_cors_origins_default():
    """Test that CORS origins have sensible defaults."""
    settings = Settings()

    assert isinstance(settings.CORS_ORIGINS, list)
    assert len(settings.CORS_ORIGINS) > 0
    assert "http://localhost:3000" in settings.CORS_ORIGINS


def test_database_url_fallback():
    """Test database URL fallback for local development."""
    settings = Settings()

    # If DATABASE_URL is not set, should provide a fallback
    db_url = settings.get_database_url()
    assert db_url is not None
    assert "postgresql://" in db_url


def test_redis_url_fallback():
    """Test Redis URL fallback for local development."""
    settings = Settings()

    # If REDIS_URL is not set, should provide a fallback
    redis_url = settings.get_redis_url()
    assert redis_url is not None
    assert "redis://" in redis_url


def test_is_production():
    """Test environment detection for production."""
    # Test production environment
    settings = Settings(ENVIRONMENT="production")
    assert settings.is_production() is True
    assert settings.is_development() is False

    # Test development environment
    settings = Settings(ENVIRONMENT="development")
    assert settings.is_production() is False
    assert settings.is_development() is True


def test_rate_limiting_settings():
    """Test rate limiting configuration."""
    settings = Settings()

    assert settings.RATE_LIMIT_ENABLED is True
    assert settings.RATE_LIMIT_TIER_ANONYMOUS > 0
    assert settings.RATE_LIMIT_TIER_FREE > settings.RATE_LIMIT_TIER_ANONYMOUS
    assert settings.RATE_LIMIT_TIER_PRO > settings.RATE_LIMIT_TIER_FREE


def test_caching_settings():
    """Test caching configuration."""
    settings = Settings()

    assert settings.CACHE_ENABLED is True
    assert settings.CACHE_TTL_GAMES > 0
    assert settings.CACHE_TTL_ANALYSIS > 0
    assert settings.CACHE_TTL_USER_PROFILE > 0


def test_stockfish_settings():
    """Test Stockfish configuration."""
    settings = Settings()

    assert settings.STOCKFISH_PATH is not None
    assert settings.STOCKFISH_DEPTH > 0
    assert settings.STOCKFISH_THREADS > 0
    assert settings.STOCKFISH_HASH > 0


def test_secret_key_generation():
    """Test that secret key is generated if not provided."""
    settings = Settings()

    assert settings.SECRET_KEY is not None
    assert len(settings.SECRET_KEY) > 0


def test_get_settings_cached():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    # Should return the same instance due to lru_cache
    assert settings1 is settings2


def test_environment_override():
    """Test that environment variables can override defaults."""
    # This test would require setting actual env vars
    # For now, we test that the Settings class accepts overrides
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=True,
        LOG_LEVEL="DEBUG",
    )

    assert settings.ENVIRONMENT == "production"
    assert settings.DEBUG is True
    assert settings.LOG_LEVEL == "DEBUG"


def test_database_pool_settings():
    """Test database connection pool configuration."""
    settings = Settings()

    # Should be optimized for Neon free tier
    assert settings.DATABASE_POOL_SIZE == 5
    assert settings.DATABASE_MAX_OVERFLOW == 2
    assert settings.DATABASE_POOL_RECYCLE > 0
    assert settings.DATABASE_POOL_PRE_PING is True
