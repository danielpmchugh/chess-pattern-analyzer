"""
Tests for custom exceptions.

This module tests all custom exception classes to ensure they
generate proper error responses with correct status codes.
"""

import pytest
from app.core.exceptions import (
    ChessAnalyzerException,
    UserNotFoundException,
    InvalidUsernameException,
    RateLimitExceededException,
    AnalysisFailedException,
    NoGamesFoundException,
    InsufficientGamesException,
    ChessComAPIException,
    ExternalAPITimeoutException,
    StockfishException,
    InvalidFENException,
    CacheException,
    DatabaseException,
    RecordNotFoundException,
    ValidationException,
    SessionException,
    SessionExpiredException,
)


def test_base_exception():
    """Test ChessAnalyzerException base class."""
    exc = ChessAnalyzerException(
        message="Test error",
        status_code=500,
        details={"key": "value"}
    )

    assert exc.message == "Test error"
    assert exc.status_code == 500
    assert exc.details == {"key": "value"}
    assert str(exc) == "Test error"


def test_user_not_found_exception():
    """Test UserNotFoundException."""
    exc = UserNotFoundException(username="testuser")

    assert "testuser" in exc.message
    assert exc.status_code == 404
    assert exc.details["username"] == "testuser"
    assert exc.details["error_type"] == "user_not_found"


def test_invalid_username_exception():
    """Test InvalidUsernameException."""
    exc = InvalidUsernameException(username="bad@user", reason="Contains invalid characters")

    assert "bad@user" in exc.message
    assert exc.status_code == 400
    assert exc.details["username"] == "bad@user"
    assert exc.details["reason"] == "Contains invalid characters"
    assert exc.details["error_type"] == "invalid_username"


def test_rate_limit_exceeded_exception():
    """Test RateLimitExceededException."""
    exc = RateLimitExceededException(
        reset_time="2024-01-01T00:00:00Z",
        limit=100,
        tier="free"
    )

    assert exc.status_code == 429
    assert exc.details["reset_time"] == "2024-01-01T00:00:00Z"
    assert exc.details["limit"] == 100
    assert exc.details["tier"] == "free"
    assert exc.details["error_type"] == "rate_limit_exceeded"


def test_analysis_failed_exception():
    """Test AnalysisFailedException."""
    exc = AnalysisFailedException(reason="Stockfish timeout", game_id="12345")

    assert "Stockfish timeout" in exc.message
    assert exc.status_code == 500
    assert exc.details["reason"] == "Stockfish timeout"
    assert exc.details["game_id"] == "12345"
    assert exc.details["error_type"] == "analysis_failed"


def test_no_games_found_exception():
    """Test NoGamesFoundException."""
    exc = NoGamesFoundException(
        username="testuser",
        filters={"time_class": "blitz"}
    )

    assert "testuser" in exc.message
    assert exc.status_code == 404
    assert exc.details["username"] == "testuser"
    assert exc.details["filters"]["time_class"] == "blitz"
    assert exc.details["error_type"] == "no_games_found"


def test_insufficient_games_exception():
    """Test InsufficientGamesException."""
    exc = InsufficientGamesException(
        username="newuser",
        game_count=5,
        minimum_required=10
    )

    assert "newuser" in exc.message
    assert exc.status_code == 400
    assert exc.details["game_count"] == 5
    assert exc.details["minimum_required"] == 10
    assert exc.details["error_type"] == "insufficient_games"


def test_chess_com_api_exception():
    """Test ChessComAPIException."""
    exc = ChessComAPIException(
        message="API returned 404",
        status_code=502,
        endpoint="/pub/player/testuser"
    )

    assert "API returned 404" in exc.message
    assert exc.status_code == 502
    assert exc.details["endpoint"] == "/pub/player/testuser"
    assert exc.details["error_type"] == "chess_com_api_error"


def test_external_api_timeout_exception():
    """Test ExternalAPITimeoutException."""
    exc = ExternalAPITimeoutException(service="Chess.com", timeout=10)

    assert "Chess.com" in exc.message
    assert exc.status_code == 504
    assert exc.details["service"] == "Chess.com"
    assert exc.details["timeout"] == 10
    assert exc.details["error_type"] == "external_api_timeout"


def test_stockfish_exception():
    """Test StockfishException."""
    exc = StockfishException(
        message="Engine crashed",
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )

    assert "Engine crashed" in exc.message
    assert exc.status_code == 500
    assert exc.details["fen"] is not None
    assert exc.details["error_type"] == "stockfish_error"


def test_invalid_fen_exception():
    """Test InvalidFENException."""
    exc = InvalidFENException(fen="invalid", reason="Invalid board state")

    assert "Invalid FEN notation" in exc.message
    assert exc.status_code == 400
    assert exc.details["fen"] == "invalid"
    assert exc.details["reason"] == "Invalid board state"
    assert exc.details["error_type"] == "invalid_fen"


def test_cache_exception():
    """Test CacheException."""
    exc = CacheException(
        operation="get",
        key="user:123",
        reason="Connection timeout"
    )

    assert "get" in exc.message
    assert exc.status_code == 500
    assert exc.details["operation"] == "get"
    assert exc.details["key"] == "user:123"
    assert exc.details["reason"] == "Connection timeout"
    assert exc.details["error_type"] == "cache_error"


def test_database_exception():
    """Test DatabaseException."""
    exc = DatabaseException(operation="insert", reason="Unique constraint violation")

    assert "insert" in exc.message
    assert exc.status_code == 500
    assert exc.details["operation"] == "insert"
    assert exc.details["reason"] == "Unique constraint violation"
    assert exc.details["error_type"] == "database_error"


def test_record_not_found_exception():
    """Test RecordNotFoundException."""
    exc = RecordNotFoundException(model="User", identifier="123")

    assert "User" in exc.message
    assert exc.status_code == 404
    assert exc.details["model"] == "User"
    assert exc.details["identifier"] == "123"
    assert exc.details["error_type"] == "record_not_found"


def test_validation_exception():
    """Test ValidationException."""
    exc = ValidationException(
        field="username",
        value="ab",
        reason="Must be at least 3 characters"
    )

    assert "username" in exc.message
    assert exc.status_code == 400
    assert exc.details["field"] == "username"
    assert exc.details["value"] == "ab"
    assert exc.details["reason"] == "Must be at least 3 characters"
    assert exc.details["error_type"] == "validation_error"


def test_session_exception():
    """Test SessionException."""
    exc = SessionException(message="Invalid session", session_id="sess_123")

    assert "Invalid session" in exc.message
    assert exc.status_code == 400
    assert exc.details["session_id"] == "sess_123"
    assert exc.details["error_type"] == "session_error"


def test_session_expired_exception():
    """Test SessionExpiredException."""
    exc = SessionExpiredException(session_id="sess_123")

    assert "expired" in exc.message.lower()
    assert exc.status_code == 401
    assert exc.details["session_id"] == "sess_123"
    assert exc.details["error_type"] == "session_expired"


def test_exception_with_none_details():
    """Test that exceptions work with None details."""
    exc = ChessAnalyzerException(message="Test", status_code=400, details=None)

    assert exc.details == {}
