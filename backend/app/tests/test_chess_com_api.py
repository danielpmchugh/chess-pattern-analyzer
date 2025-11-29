"""
Unit tests for Chess.com API client.

Tests the ChessComAPIClient service with mocked HTTP responses.
"""

import json
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
import httpx

from app.services.chess_com import ChessComAPIClient
from app.models.chess_com import PlayerProfile, ChessGame, ParsedGame
from app.core.exceptions import (
    UserNotFoundException,
    ChessComAPIException,
    RateLimitExceededException,
    ExternalAPITimeoutException,
    NoGamesFoundException,
)


# Sample test data
SAMPLE_PLAYER_PROFILE = {
    "username": "testuser",
    "player_id": 12345678,
    "url": "https://www.chess.com/member/testuser",
    "name": "Test User",
    "followers": 100,
    "last_online": 1700000000,
    "joined": 1600000000,
    "status": "basic",
    "is_streamer": False,
}

SAMPLE_GAME = {
    "url": "https://www.chess.com/game/live/12345678",
    "pgn": """[Event "Live Chess"]
[Site "Chess.com"]
[Date "2024.01.15"]
[Round "?"]
[White "player1"]
[Black "player2"]
[Result "1-0"]
[ECO "C50"]
[WhiteElo "1500"]
[BlackElo "1480"]
[TimeControl "600"]
[EndTime "10:30:00 PST"]
[Termination "player1 won by checkmate"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. d3 d6 1-0
""",
    "time_control": "600",
    "end_time": 1705329000,
    "rated": True,
    "uuid": "test-game-123",
    "time_class": "rapid",
    "rules": "chess",
    "white": {
        "username": "player1",
        "rating": 1500,
        "result": "win",
        "@id": "https://api.chess.com/pub/player/player1",
    },
    "black": {
        "username": "player2",
        "rating": 1480,
        "result": "checkmated",
        "@id": "https://api.chess.com/pub/player/player2",
    },
}


class TestChessComAPIClient:
    """Test suite for ChessComAPIClient."""

    @pytest.fixture
    async def mock_redis(self):
        """Create a mock Redis client."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()
        return redis

    @pytest.fixture
    async def client(self, mock_redis):
        """Create a ChessComAPIClient instance with mocked dependencies."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        client = ChessComAPIClient(
            redis_client=mock_redis,
            http_client=mock_http,
        )
        await client.__aenter__()
        yield client
        await client.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_get_player_profile_success(self, client, mock_redis):
        """Test successful player profile fetch."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_PLAYER_PROFILE

        client._http_client.get = AsyncMock(return_value=mock_response)

        # Execute
        profile = await client.get_player_profile("testuser")

        # Verify
        assert isinstance(profile, PlayerProfile)
        assert profile.username == "testuser"
        assert profile.player_id == 12345678
        client._http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_player_profile_cached(self, client, mock_redis):
        """Test player profile retrieval from cache."""
        # Setup cache hit
        mock_redis.get = AsyncMock(return_value=json.dumps(SAMPLE_PLAYER_PROFILE))

        # Execute
        profile = await client.get_player_profile("testuser")

        # Verify
        assert isinstance(profile, PlayerProfile)
        assert profile.username == "testuser"
        # HTTP client should not be called
        client._http_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_player_profile_not_found(self, client):
        """Test player profile fetch for non-existent user."""
        # Setup 404 response
        mock_response = Mock()
        mock_response.status_code = 404

        client._http_client.get = AsyncMock(return_value=mock_response)

        # Execute and verify exception
        with pytest.raises(UserNotFoundException) as exc_info:
            await client.get_player_profile("nonexistentuser")

        assert "nonexistentuser" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_monthly_games_success(self, client, mock_redis):
        """Test successful monthly games fetch."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"games": [SAMPLE_GAME]}

        client._http_client.get = AsyncMock(return_value=mock_response)

        # Execute
        games = await client.get_monthly_games("testuser", 2024, 1)

        # Verify
        assert isinstance(games, list)
        assert len(games) == 1
        assert isinstance(games[0], ChessGame)
        assert games[0].uuid == "test-game-123"

    @pytest.mark.asyncio
    async def test_get_monthly_games_empty(self, client, mock_redis):
        """Test monthly games fetch with no games."""
        # Setup empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"games": []}

        client._http_client.get = AsyncMock(return_value=mock_response)

        # Execute
        games = await client.get_monthly_games("testuser", 2024, 1)

        # Verify
        assert isinstance(games, list)
        assert len(games) == 0

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self, client):
        """Test retry behavior on rate limit (429)."""
        # Setup 429 response followed by success
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = SAMPLE_PLAYER_PROFILE

        client._http_client.get = AsyncMock(
            side_effect=[mock_response_429, mock_response_200]
        )

        # Execute
        profile = await client.get_player_profile("testuser")

        # Verify retry occurred
        assert client._http_client.get.call_count == 2
        assert isinstance(profile, PlayerProfile)

    @pytest.mark.asyncio
    async def test_rate_limit_max_retries(self, client):
        """Test rate limit exception after max retries."""
        # Setup always 429 response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}

        client._http_client.get = AsyncMock(return_value=mock_response)

        # Execute and verify exception
        with pytest.raises(RateLimitExceededException):
            await client.get_player_profile("testuser")

        # Should retry MAX_RETRIES times
        assert client._http_client.get.call_count == ChessComAPIClient.MAX_RETRIES + 1

    @pytest.mark.asyncio
    async def test_server_error_retry(self, client):
        """Test retry behavior on server errors (5xx)."""
        # Setup 500 response followed by success
        mock_response_500 = Mock()
        mock_response_500.status_code = 500

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = SAMPLE_PLAYER_PROFILE

        client._http_client.get = AsyncMock(
            side_effect=[mock_response_500, mock_response_200]
        )

        # Execute
        profile = await client.get_player_profile("testuser")

        # Verify retry occurred
        assert client._http_client.get.call_count == 2
        assert isinstance(profile, PlayerProfile)

    @pytest.mark.asyncio
    async def test_timeout_exception(self, client):
        """Test timeout handling."""
        # Setup timeout
        client._http_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        # Execute and verify exception
        with pytest.raises(ExternalAPITimeoutException) as exc_info:
            await client.get_player_profile("testuser")

        assert "Chess.com" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_player_archives(self, client, mock_redis):
        """Test player archives fetch."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "archives": [
                "https://api.chess.com/pub/player/testuser/games/2024/01",
                "https://api.chess.com/pub/player/testuser/games/2024/02",
            ]
        }

        client._http_client.get = AsyncMock(return_value=mock_response)

        # Execute
        archives = await client.get_player_archives("testuser")

        # Verify
        assert isinstance(archives, list)
        assert len(archives) == 2
        assert all(isinstance(url, str) for url in archives)

    @pytest.mark.asyncio
    async def test_get_recent_games(self, client, mock_redis):
        """Test recent games fetch."""
        # Setup mock responses
        mock_response_profile = Mock()
        mock_response_profile.status_code = 200
        mock_response_profile.json.return_value = SAMPLE_PLAYER_PROFILE

        mock_response_games = Mock()
        mock_response_games.status_code = 200
        mock_response_games.json.return_value = {"games": [SAMPLE_GAME]}

        client._http_client.get = AsyncMock(
            side_effect=[mock_response_profile, mock_response_games]
        )

        # Execute
        games = await client.get_recent_games("testuser", count=10, days=30)

        # Verify
        assert isinstance(games, list)
        assert len(games) > 0

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, client):
        """Test cache key generation."""
        key1 = client._get_cache_key("test", "user1", 2024, 1)
        key2 = client._get_cache_key("test", "user1", 2024, 1)
        key3 = client._get_cache_key("test", "user2", 2024, 1)

        # Same parameters should generate same key
        assert key1 == key2
        # Different parameters should generate different keys
        assert key1 != key3
        # Key should have proper format
        assert key1.startswith("chess_com:")

    @pytest.mark.asyncio
    async def test_username_normalization(self, client, mock_redis):
        """Test that usernames are normalized (lowercase, trimmed)."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_PLAYER_PROFILE

        client._http_client.get = AsyncMock(return_value=mock_response)

        # Test with uppercase and whitespace
        await client.get_player_profile("  TESTUSER  ")

        # Verify the call used lowercase without whitespace
        call_args = client._http_client.get.call_args[0][0]
        assert "testuser" in call_args.lower()
        assert "TESTUSER" not in call_args

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, mock_redis):
        """Test async context manager lifecycle."""
        client = ChessComAPIClient(redis_client=mock_redis)

        # Before entering context
        assert client._http_client is None

        # Enter context
        async with client:
            # HTTP client should be initialized
            assert client._http_client is not None

        # After exiting context
        # HTTP client should be closed (if owned)
        # Note: Can't easily test closure without inspecting internals

    @pytest.mark.asyncio
    async def test_get_games_in_date_range_no_games(self, client, mock_redis):
        """Test date range query with no games found."""
        # Setup profile response
        mock_response_profile = Mock()
        mock_response_profile.status_code = 200
        mock_response_profile.json.return_value = SAMPLE_PLAYER_PROFILE

        # Setup empty games response
        mock_response_games = Mock()
        mock_response_games.status_code = 200
        mock_response_games.json.return_value = {"games": []}

        client._http_client.get = AsyncMock(
            side_effect=[mock_response_profile, mock_response_games]
        )

        # Execute and verify exception
        with pytest.raises(NoGamesFoundException):
            await client.get_games_in_date_range(
                "testuser",
                date(2024, 1, 1),
                date(2024, 1, 31),
            )


class TestChessComAPIClientIntegration:
    """Integration tests with more realistic scenarios."""

    @pytest.fixture
    async def client_no_cache(self):
        """Create client without caching for integration tests."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        client = ChessComAPIClient(
            redis_client=None,
            http_client=mock_http,
        )
        await client.__aenter__()
        yield client
        await client.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_multiple_months_fetch(self, client_no_cache):
        """Test fetching games across multiple months."""
        # Setup mock responses for profile and multiple months
        mock_response_profile = Mock()
        mock_response_profile.status_code = 200
        mock_response_profile.json.return_value = SAMPLE_PLAYER_PROFILE

        mock_response_games_1 = Mock()
        mock_response_games_1.status_code = 200
        mock_response_games_1.json.return_value = {"games": [SAMPLE_GAME]}

        mock_response_games_2 = Mock()
        mock_response_games_2.status_code = 200
        mock_response_games_2.json.return_value = {"games": [SAMPLE_GAME]}

        client_no_cache._http_client.get = AsyncMock(
            side_effect=[
                mock_response_profile,
                mock_response_games_1,
                mock_response_games_2,
            ]
        )

        # Execute
        games = await client_no_cache.get_games_in_date_range(
            "testuser",
            date(2024, 1, 1),
            date(2024, 2, 28),
        )

        # Verify multiple API calls were made
        assert client_no_cache._http_client.get.call_count >= 2

    @pytest.mark.asyncio
    async def test_max_games_limit(self, client_no_cache):
        """Test that max_games parameter limits results."""
        # Setup responses with many games
        multiple_games = [SAMPLE_GAME.copy() for _ in range(50)]
        for i, game in enumerate(multiple_games):
            game["uuid"] = f"test-game-{i}"

        mock_response_profile = Mock()
        mock_response_profile.status_code = 200
        mock_response_profile.json.return_value = SAMPLE_PLAYER_PROFILE

        mock_response_games = Mock()
        mock_response_games.status_code = 200
        mock_response_games.json.return_value = {"games": multiple_games}

        client_no_cache._http_client.get = AsyncMock(
            side_effect=[mock_response_profile, mock_response_games]
        )

        # Execute with limit
        games = await client_no_cache.get_games_in_date_range(
            "testuser",
            date(2024, 1, 1),
            date(2024, 1, 31),
            max_games=10,
        )

        # Verify limit was applied
        assert len(games) <= 10
