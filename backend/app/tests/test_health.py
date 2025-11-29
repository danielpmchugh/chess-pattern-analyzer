"""
Tests for health check endpoints.

This module tests all health check endpoints to ensure they
return proper status codes and response formats.
"""

import pytest
from fastapi import status


def test_root_endpoint(client):
    """Test the root endpoint returns API information."""
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "operational"
    assert "documentation" in data
    assert "endpoints" in data


def test_healthz_endpoint(client):
    """Test the /healthz endpoint for Railway."""
    response = client.get("/healthz")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_health_check_endpoint(client):
    """Test basic health check endpoint."""
    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "chess-pattern-analyzer"
    assert "version" in data
    assert "environment" in data


def test_liveness_probe(client):
    """Test liveness probe endpoint."""
    response = client.get("/api/v1/health/live")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_readiness_probe(client):
    """Test readiness probe endpoint."""
    response = client.get("/api/v1/health/ready")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "timestamp" in data

    # Verify expected checks exist
    checks = data["checks"]
    assert "api" in checks
    assert "redis" in checks
    assert "stockfish" in checks
    assert "database" in checks

    # API should always be ready
    assert checks["api"] == "ready"


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = client.get("/api/v1/health/metrics")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "uptime_seconds" in data
    assert "requests_total" in data
    assert "requests_per_second" in data
    assert "average_response_time_ms" in data
    assert "active_sessions" in data
    assert "analyses_completed" in data
    assert "cache_hit_rate" in data
    assert "timestamp" in data


def test_info_endpoint(client):
    """Test system info endpoint."""
    response = client.get("/api/v1/health/info")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "service" in data
    assert "configuration" in data
    assert "deployment" in data
    assert "integrations" in data
    assert "timestamp" in data

    # Verify service information
    service = data["service"]
    assert "name" in service
    assert "version" in service
    assert "environment" in service

    # Verify configuration
    config = data["configuration"]
    assert "debug_mode" in config
    assert "log_level" in config
    assert "rate_limiting_enabled" in config
    assert "cache_enabled" in config

    # Verify integrations
    integrations = data["integrations"]
    assert "chess_com_api" in integrations
    assert "stockfish_path" in integrations
    assert "redis_configured" in integrations
    assert "database_configured" in integrations


def test_openapi_docs(client):
    """Test that OpenAPI documentation is accessible."""
    response = client.get("/api/docs")

    # Should return HTML for Swagger UI
    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]


def test_openapi_json(client):
    """Test that OpenAPI JSON schema is accessible."""
    response = client.get("/api/openapi.json")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data

    # Verify our endpoints are documented
    paths = data["paths"]
    assert "/" in paths
    assert "/api/v1/health" in paths
    assert "/api/v1/health/live" in paths
    assert "/api/v1/health/ready" in paths


def test_request_id_header(client):
    """Test that all responses include request ID header."""
    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_cors_headers(client):
    """Test that CORS headers are present."""
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3000"}
    )

    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers
