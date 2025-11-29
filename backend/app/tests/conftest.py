"""
Pytest configuration and fixtures for testing.

This module provides common test fixtures and configuration
for all tests in the Chess Pattern Analyzer API.
"""

import pytest
from fastapi.testclient import TestClient
from typing import Generator

from app.main import app
from app.config import settings


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Create a test client for the FastAPI application.

    Yields:
        TestClient instance for making test requests
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_settings():
    """
    Provide test settings.

    Returns:
        Settings instance for testing
    """
    return settings


@pytest.fixture
def sample_username() -> str:
    """
    Provide a sample Chess.com username for testing.

    Returns:
        A valid Chess.com username
    """
    return "hikaru"


@pytest.fixture
def sample_invalid_username() -> str:
    """
    Provide an invalid username for testing error cases.

    Returns:
        An invalid username
    """
    return "invalid@username!"
