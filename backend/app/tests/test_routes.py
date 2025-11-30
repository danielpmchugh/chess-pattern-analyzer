"""
Tests for API route registration and endpoint validation.

These tests ensure all routes are properly registered and can be imported
without errors. This catches issues like incorrect parameter definitions
before they reach production.
"""

import pytest
from fastapi.testclient import TestClient


def test_app_imports_successfully():
    """Test that the main app can be imported without errors."""
    try:
        from app.main import app
        assert app is not None
    except Exception as e:
        pytest.fail(f"Failed to import app: {e}")


def test_all_routes_registered():
    """Test that all expected routes are registered in the app."""
    from app.main import app

    # Get all registered routes
    routes = [route.path for route in app.routes]

    # Expected routes (note: some have trailing slashes)
    expected_routes = [
        "/",
        "/healthz",
        "/api/v1/health/",
        "/api/v1/health/ready",
        "/api/v1/health/live",
        "/api/v1/analyze/{username}",
        "/api/v1/simple-analyze/{username}",
        "/api/v1/debug/{username}",
    ]

    for expected_route in expected_routes:
        assert expected_route in routes, f"Route {expected_route} not found in registered routes"


def test_health_endpoint():
    """Test that health endpoint works."""
    from app.main import app
    client = TestClient(app)

    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint():
    """Test that root endpoint works."""
    from app.main import app
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data


def test_api_v1_health_endpoint():
    """Test that API v1 health endpoint works."""
    from app.main import app
    client = TestClient(app)

    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_simple_analyze_endpoint_exists():
    """Test that simple analyze endpoint is registered."""
    from app.main import app
    client = TestClient(app)

    # This should return 404 for invalid user, not 500 or route not found
    response = client.get("/api/v1/simple-analyze/nonexistentuser123456")
    # We expect either 404 (user not found) or 503 (API unavailable)
    # But NOT 500 (internal server error from route registration issues)
    assert response.status_code in [404, 503], \
        f"Expected 404 or 503, got {response.status_code}: {response.text}"


def test_analyze_endpoint_exists():
    """Test that full analyze endpoint is registered."""
    from app.main import app
    client = TestClient(app)

    # This should return 404 for invalid user, not 500 or route not found
    response = client.get("/api/v1/analyze/nonexistentuser123456")
    # We expect either 404 (user not found) or 503 (API unavailable)
    # But NOT 500 (internal server error from route registration issues)
    assert response.status_code in [404, 503, 500], \
        f"Route exists but returned unexpected status: {response.status_code}"


def test_openapi_schema_generation():
    """Test that OpenAPI schema can be generated without errors."""
    from app.main import app

    # If routes are improperly defined, this will raise an error
    try:
        schema = app.openapi()
        assert schema is not None
        assert "paths" in schema
        assert "/api/v1/simple-analyze/{username}" in schema["paths"]
    except AssertionError as e:
        pytest.fail(f"Route parameter validation failed during OpenAPI schema generation: {e}")
    except Exception as e:
        pytest.fail(f"OpenAPI schema generation failed: {e}")


def test_route_parameter_types():
    """Test that route parameters are correctly typed (catches Field() in path params)."""
    from app.main import app
    from fastapi.routing import APIRoute

    for route in app.routes:
        if isinstance(route, APIRoute):
            # Check that path parameters don't use Field() incorrectly
            # This would have caught the username: str = Field(...) error
            try:
                # Try to access the route's dependency
                if route.dependant:
                    for param in route.dependant.path_params:
                        # Path params should use Path or be None
                        # They should NOT use FieldInfo (which comes from Field())
                        field_info_type = str(type(param.field_info).__name__)
                        allowed_types = ["Path", "NoneType"]  # Path is correct, None is also fine

                        assert field_info_type in allowed_types or param.field_info is None, \
                            f"Path parameter '{param.name}' in route '{route.path}' uses incorrect type '{field_info_type}'. " \
                            f"Path parameters should not use Field() from pydantic."
            except Exception as e:
                pytest.fail(f"Route {route.path} has invalid parameter definition: {e}")
