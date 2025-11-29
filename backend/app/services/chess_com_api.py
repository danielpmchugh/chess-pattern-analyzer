"""
Chess.com Published-Data API client.

This module provides a robust client for fetching public game data from Chess.com
without requiring authentication. Includes rate limiting, caching, and error handling.
"""
import asyncio
import time
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import logging

import httpx
from app.models.game import (
    ChessGame,
    PlayerProfile,
    PlayerStats,
    MonthlyGamesArchive,
    GamesArchiveList,
)
from app.core.exceptions import (
    UserNotFoundError,
    ChessComAPIError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts request interval based on API responses.

    Starts with conservative interval and adjusts based on whether rate limits
    are encountered.
    """

    def __init__(self, initial_interval: float = 0.5):
        """
        Initialize rate limiter.

        Args:
            initial_interval: Starting interval between requests in seconds
        """
        self.last_request = 0.0
        self.min_interval = initial_interval
        self.max_interval = 10.0  # Max 10 seconds between requests
        self.min_min_interval = 0.1  # Absolute minimum 100ms

    async def wait_if_needed(self) -> None:
        """Wait if needed to respect rate limit."""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self.last_request = time.time()

    def adjust_rate(self, got_rate_limited: bool) -> None:
        """
        Adjust rate limit interval based on response.

        Args:
            got_rate_limited: True if received 429 response
        """
        if got_rate_limited:
            # Exponentially back off
            self.min_interval = min(self.min_interval * 2, self.max_interval)
            logger.warning(f"Rate limited! Increasing interval to {self.min_interval:.2f}s")
        else:
            # Gradually speed up
            self.min_interval = max(self.min_interval * 0.95, self.min_min_interval)


class GameCache:
    """
    Simple in-memory cache for game data with TTL.

    Chess.com data refreshes at most every 12 hours, so we cache with that TTL.
    """

    def __init__(self, ttl: int = 43200):  # 12 hours default
        """
        Initialize cache.

        Args:
            ttl: Time-to-live in seconds
        """
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.ttl = ttl

    def cache_key(self, username: str, year: int, month: int) -> str:
        """Generate cache key."""
        return f"{username.lower()}:{year}:{month:02d}"

    def get(self, username: str, year: int, month: int) -> Optional[List[ChessGame]]:
        """Get cached games if available and not expired."""
        key = self.cache_key(username, year, month)
        if key in self.cache:
            games, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache hit for {key}")
                return games
            else:
                logger.debug(f"Cache expired for {key}")
                del self.cache[key]
        return None

    def set(self, username: str, year: int, month: int, games: List[ChessGame]) -> None:
        """Cache games with timestamp."""
        key = self.cache_key(username, year, month)
        self.cache[key] = (games, time.time())
        logger.debug(f"Cached {len(games)} games for {key}")

    def clear(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Cache cleared")


class ChessComAPIClient:
    """
    Client for Chess.com Published-Data API.

    Handles fetching player data, games, and statistics from Chess.com's public API
    without requiring authentication.
    """

    BASE_URL = "https://api.chess.com/pub"

    def __init__(
        self,
        rate_limiter: Optional[AdaptiveRateLimiter] = None,
        cache: Optional[GameCache] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize Chess.com API client.

        Args:
            rate_limiter: Optional custom rate limiter
            cache: Optional custom cache
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.rate_limiter = rate_limiter or AdaptiveRateLimiter()
        self.cache = cache or GameCache()
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "ChessPatternAnalyzer/1.0 (Educational Project)",
                "Accept": "application/json",
            },
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def _make_request(
        self,
        endpoint: str,
        retries: int = 0,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with rate limiting and retry logic.

        Args:
            endpoint: API endpoint (relative to BASE_URL)
            retries: Current retry attempt

        Returns:
            JSON response data

        Raises:
            UserNotFoundError: If username not found (404)
            RateLimitError: If rate limited (429)
            ChessComAPIError: For other API errors
        """
        await self.rate_limiter.wait_if_needed()

        url = f"{self.BASE_URL}/{endpoint}"
        logger.debug(f"Requesting: {url}")

        try:
            response = await self.client.get(url)

            if response.status_code == 200:
                self.rate_limiter.adjust_rate(got_rate_limited=False)
                return response.json()

            elif response.status_code == 404:
                raise UserNotFoundError(f"Resource not found: {endpoint}")

            elif response.status_code == 429:
                self.rate_limiter.adjust_rate(got_rate_limited=True)
                retry_after = int(response.headers.get("Retry-After", 60))

                if retries < self.max_retries:
                    logger.warning(f"Rate limited. Retrying after {retry_after}s (attempt {retries + 1}/{self.max_retries})")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(endpoint, retries + 1)
                else:
                    raise RateLimitError(
                        f"Rate limit exceeded after {self.max_retries} retries",
                        retry_after=retry_after,
                    )

            else:
                error_msg = f"API error {response.status_code}: {response.text}"
                logger.error(error_msg)

                if retries < self.max_retries and response.status_code >= 500:
                    # Retry on server errors with exponential backoff
                    wait_time = 2 ** retries
                    logger.warning(f"Server error. Retrying after {wait_time}s")
                    await asyncio.sleep(wait_time)
                    return await self._make_request(endpoint, retries + 1)

                raise ChessComAPIError(error_msg)

        except httpx.TimeoutException as e:
            if retries < self.max_retries:
                wait_time = 2 ** retries
                logger.warning(f"Request timeout. Retrying after {wait_time}s")
                await asyncio.sleep(wait_time)
                return await self._make_request(endpoint, retries + 1)
            raise ChessComAPIError(f"Request timeout after {self.max_retries} retries") from e

        except httpx.HTTPError as e:
            raise ChessComAPIError(f"HTTP error: {str(e)}") from e

    async def get_player_profile(self, username: str) -> PlayerProfile:
        """
        Fetch player profile.

        Args:
            username: Chess.com username

        Returns:
            Player profile data

        Raises:
            UserNotFoundError: If username doesn't exist
            ChessComAPIError: For other API errors
        """
        username = username.lower()
        data = await self._make_request(f"player/{username}")
        return PlayerProfile(**data)

    async def get_player_stats(self, username: str) -> PlayerStats:
        """
        Fetch player statistics.

        Args:
            username: Chess.com username

        Returns:
            Player statistics

        Raises:
            UserNotFoundError: If username doesn't exist
            ChessComAPIError: For other API errors
        """
        username = username.lower()
        data = await self._make_request(f"player/{username}/stats")
        return PlayerStats(**data)

    async def get_player_games(
        self,
        username: str,
        year: int,
        month: int,
    ) -> List[ChessGame]:
        """
        Fetch games for a specific month.

        Args:
            username: Chess.com username
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            List of games for that month

        Raises:
            UserNotFoundError: If username doesn't exist or no games for that month
            ChessComAPIError: For other API errors
        """
        username = username.lower()

        # Check cache first
        cached_games = self.cache.get(username, year, month)
        if cached_games is not None:
            return cached_games

        # Fetch from API
        data = await self._make_request(f"player/{username}/games/{year}/{month:02d}")
        archive = MonthlyGamesArchive(**data)

        # Cache the results
        self.cache.set(username, year, month, archive.games)

        return archive.games

    async def get_games_archive_list(self, username: str) -> GamesArchiveList:
        """
        Get list of available monthly game archives.

        Args:
            username: Chess.com username

        Returns:
            List of archive URLs

        Raises:
            UserNotFoundError: If username doesn't exist
            ChessComAPIError: For other API errors
        """
        username = username.lower()
        data = await self._make_request(f"player/{username}/games/archives")
        return GamesArchiveList(**data)

    async def fetch_game_range(
        self,
        username: str,
        start_date: date,
        end_date: date,
        max_games: Optional[int] = None,
    ) -> List[ChessGame]:
        """
        Fetch all games in a date range.

        Args:
            username: Chess.com username
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            max_games: Optional maximum number of games to fetch

        Returns:
            List of games in date range

        Raises:
            UserNotFoundError: If username doesn't exist
            ChessComAPIError: For other API errors
        """
        username = username.lower()
        all_games: List[ChessGame] = []

        # Generate list of (year, month) tuples to fetch
        current = date(start_date.year, start_date.month, 1)
        end = date(end_date.year, end_date.month, 1)

        while current <= end:
            logger.info(f"Fetching games for {username} - {current.year}/{current.month:02d}")

            try:
                games = await self.get_player_games(username, current.year, current.month)

                # Filter games by date range
                for game in games:
                    game_date = game.end_datetime.date()
                    if start_date <= game_date <= end_date:
                        all_games.append(game)

                        if max_games and len(all_games) >= max_games:
                            logger.info(f"Reached max_games limit: {max_games}")
                            return all_games

            except UserNotFoundError:
                # No games for this month, continue
                logger.debug(f"No games found for {current.year}/{current.month:02d}")

            # Move to next month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

        logger.info(f"Fetched {len(all_games)} games for {username}")
        return all_games

    async def fetch_recent_games(
        self,
        username: str,
        count: int = 100,
    ) -> List[ChessGame]:
        """
        Fetch the most recent N games for a player.

        Args:
            username: Chess.com username
            count: Number of recent games to fetch

        Returns:
            List of recent games (newest first)

        Raises:
            UserNotFoundError: If username doesn't exist
            ChessComAPIError: For other API errors
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=180)  # Look back 6 months

        games = await self.fetch_game_range(username, start_date, end_date, max_games=count)

        # Sort by end_time descending (newest first)
        games.sort(key=lambda g: g.end_time, reverse=True)

        return games[:count]
