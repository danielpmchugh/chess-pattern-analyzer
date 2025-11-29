"""
Custom exceptions for Chess Pattern Analyzer API.

This module defines application-specific exceptions with proper
HTTP status codes and structured error responses.
"""

from typing import Optional, Dict, Any


class ChessAnalyzerException(Exception):
    """
    Base exception for all application-specific errors.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code for the error
        details: Additional error context and metadata
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# User-related exceptions


class UserNotFoundException(ChessAnalyzerException):
    """Chess.com user not found or does not exist."""

    def __init__(self, username: str):
        super().__init__(
            message=f"Chess.com user '{username}' not found",
            status_code=404,
            details={"username": username, "error_type": "user_not_found"},
        )


class InvalidUsernameException(ChessAnalyzerException):
    """Username format is invalid."""

    def __init__(self, username: str, reason: str = "Invalid format"):
        super().__init__(
            message=f"Invalid username '{username}': {reason}",
            status_code=400,
            details={
                "username": username,
                "reason": reason,
                "error_type": "invalid_username",
            },
        )


# Rate limiting exceptions


class RateLimitExceededException(ChessAnalyzerException):
    """Rate limit exceeded for the current user/IP."""

    def __init__(self, reset_time: str, limit: int = 0, tier: str = "anonymous"):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            details={
                "reset_time": reset_time,
                "limit": limit,
                "tier": tier,
                "error_type": "rate_limit_exceeded",
            },
        )


# Analysis exceptions


class AnalysisFailedException(ChessAnalyzerException):
    """Game analysis failed for some reason."""

    def __init__(self, reason: str, game_id: Optional[str] = None):
        super().__init__(
            message=f"Analysis failed: {reason}",
            status_code=500,
            details={
                "reason": reason,
                "game_id": game_id,
                "error_type": "analysis_failed",
            },
        )


class NoGamesFoundException(ChessAnalyzerException):
    """No games found for the specified criteria."""

    def __init__(self, username: str, filters: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"No games found for user '{username}'",
            status_code=404,
            details={
                "username": username,
                "filters": filters or {},
                "error_type": "no_games_found",
            },
        )


class InsufficientGamesException(ChessAnalyzerException):
    """Not enough games to perform meaningful analysis."""

    def __init__(self, username: str, game_count: int, minimum_required: int = 10):
        super().__init__(
            message=f"User '{username}' has only {game_count} games. Minimum {minimum_required} required for analysis.",
            status_code=400,
            details={
                "username": username,
                "game_count": game_count,
                "minimum_required": minimum_required,
                "error_type": "insufficient_games",
            },
        )


# External API exceptions


class ChessComAPIException(ChessAnalyzerException):
    """Chess.com API request failed."""

    def __init__(
        self, message: str, status_code: int = 502, endpoint: Optional[str] = None
    ):
        super().__init__(
            message=f"Chess.com API error: {message}",
            status_code=status_code,
            details={"endpoint": endpoint, "error_type": "chess_com_api_error"},
        )


class ExternalAPITimeoutException(ChessAnalyzerException):
    """External API request timed out."""

    def __init__(self, service: str, timeout: int):
        super().__init__(
            message=f"{service} API request timed out after {timeout} seconds",
            status_code=504,
            details={
                "service": service,
                "timeout": timeout,
                "error_type": "external_api_timeout",
            },
        )


# Engine exceptions


class StockfishException(ChessAnalyzerException):
    """Stockfish engine error."""

    def __init__(self, message: str, fen: Optional[str] = None):
        super().__init__(
            message=f"Stockfish engine error: {message}",
            status_code=500,
            details={"fen": fen, "error_type": "stockfish_error"},
        )


class InvalidFENException(ChessAnalyzerException):
    """Invalid FEN string provided."""

    def __init__(self, fen: str, reason: str = "Invalid format"):
        super().__init__(
            message=f"Invalid FEN notation: {reason}",
            status_code=400,
            details={"fen": fen, "reason": reason, "error_type": "invalid_fen"},
        )


# Cache exceptions


class CacheException(ChessAnalyzerException):
    """Cache operation failed."""

    def __init__(self, operation: str, key: str, reason: str):
        super().__init__(
            message=f"Cache {operation} failed for key '{key}': {reason}",
            status_code=500,
            details={
                "operation": operation,
                "key": key,
                "reason": reason,
                "error_type": "cache_error",
            },
        )


# Database exceptions


class DatabaseException(ChessAnalyzerException):
    """Database operation failed."""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Database {operation} failed: {reason}",
            status_code=500,
            details={
                "operation": operation,
                "reason": reason,
                "error_type": "database_error",
            },
        )


class RecordNotFoundException(ChessAnalyzerException):
    """Database record not found."""

    def __init__(self, model: str, identifier: str):
        super().__init__(
            message=f"{model} with identifier '{identifier}' not found",
            status_code=404,
            details={
                "model": model,
                "identifier": identifier,
                "error_type": "record_not_found",
            },
        )


# Validation exceptions


class ValidationException(ChessAnalyzerException):
    """Request validation failed."""

    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            message=f"Validation failed for '{field}': {reason}",
            status_code=400,
            details={
                "field": field,
                "value": str(value),
                "reason": reason,
                "error_type": "validation_error",
            },
        )


# Session exceptions


class SessionException(ChessAnalyzerException):
    """Session management error."""

    def __init__(self, message: str, session_id: Optional[str] = None):
        super().__init__(
            message=f"Session error: {message}",
            status_code=400,
            details={"session_id": session_id, "error_type": "session_error"},
        )


class SessionExpiredException(ChessAnalyzerException):
    """Session has expired."""

    def __init__(self, session_id: str):
        super().__init__(
            message="Session has expired. Please start a new analysis.",
            status_code=401,
            details={"session_id": session_id, "error_type": "session_expired"},
        )
