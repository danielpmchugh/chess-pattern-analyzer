"""
Chess.com API client service.

This module provides an async HTTP client for fetching game data from
Chess.com's Published-Data API with retry logic, caching, and error handling.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from urllib.parse import quote

import httpx
from redis import asyncio as aioredis

from app.config import settings
from app.core.exceptions import (
    ChessComAPIException,
    UserNotFoundException,
    ExternalAPITimeoutException,
    RateLimitExceededException,
    NoGamesFoundException,
)
from app.models.chess_com import (
    PlayerProfile,
    ChessGame,
    MonthlyGames,
    PlayerArchives,
    ParsedGame,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChessComAPIClient:
    """
    Async HTTP client for Chess.com Published-Data API.

    Features:
    - Exponential backoff retry logic for failed requests
    - Redis-based caching with configurable TTL
    - Comprehensive error handling
    - Rate limit awareness
    - Connection pooling optimized for serverless

    API Documentation: https://www.chess.com/news/view/published-data-api
    """

    BASE_URL = settings.CHESS_COM_API_BASE_URL
    TIMEOUT = settings.CHESS_COM_API_TIMEOUT
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 30.0  # seconds
    CACHE_TTL_PROFILE = 1800  # 30 minutes
    CACHE_TTL_GAMES = 43200  # 12 hours

    def __init__(
        self,
        redis_client: Optional[aioredis.Redis] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """
        Initialize Chess.com API client.

        Args:
            redis_client: Optional Redis client for caching
            http_client: Optional httpx client (useful for testing)
        """
        self.redis_client = redis_client
        self._http_client = http_client
        self._owned_client = http_client is None

    async def __aenter__(self):
        """Async context manager entry."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.TIMEOUT),
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                ),
                headers={
                    "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}",
                },
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._owned_client and self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def _make_request(
        self,
        endpoint: str,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            endpoint: API endpoint path
            retry_count: Current retry attempt number

        Returns:
            Parsed JSON response

        Raises:
            ChessComAPIException: For API errors
            UserNotFoundException: For 404 errors
            RateLimitExceededException: For 429 errors
            ExternalAPITimeoutException: For timeout errors
        """
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            if self._http_client is None:
                raise ChessComAPIException(
                    "HTTP client not initialized. Use async context manager.",
                    status_code=500,
                )

            logger.debug(f"Making request to Chess.com API: {endpoint}")

            response = await self._http_client.get(url)

            # Handle different status codes
            if response.status_code == 200:
                logger.debug(f"Successfully fetched: {endpoint}")
                return response.json()

            elif response.status_code == 404:
                logger.warning(f"Resource not found: {endpoint}")
                raise UserNotFoundException(endpoint.split("/")[1] if "/" in endpoint else "unknown")

            elif response.status_code == 429:
                # Rate limit hit
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limit hit. Retry after {retry_after}s")

                if retry_count < self.MAX_RETRIES:
                    await asyncio.sleep(retry_after)
                    return await self._make_request(endpoint, retry_count + 1)
                else:
                    raise RateLimitExceededException(
                        reset_time=str(datetime.now() + timedelta(seconds=retry_after)),
                        limit=0,
                        tier="chess_com_api",
                    )

            elif response.status_code >= 500:
                # Server error - retry with exponential backoff
                if retry_count < self.MAX_RETRIES:
                    delay = min(
                        self.INITIAL_RETRY_DELAY * (2 ** retry_count),
                        self.MAX_RETRY_DELAY,
                    )
                    logger.warning(
                        f"Server error {response.status_code}. "
                        f"Retrying in {delay}s (attempt {retry_count + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(delay)
                    return await self._make_request(endpoint, retry_count + 1)
                else:
                    raise ChessComAPIException(
                        f"Server error after {self.MAX_RETRIES} retries",
                        status_code=response.status_code,
                        endpoint=endpoint,
                    )

            else:
                # Other client errors
                raise ChessComAPIException(
                    f"Unexpected status code: {response.status_code}",
                    status_code=response.status_code,
                    endpoint=endpoint,
                )

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {endpoint}: {e}")
            raise ExternalAPITimeoutException("Chess.com", self.TIMEOUT)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise ChessComAPIException(
                f"HTTP error: {str(e)}",
                status_code=502,
                endpoint=endpoint,
            )

    def _get_cache_key(self, prefix: str, *args) -> str:
        """
        Generate cache key from prefix and arguments.

        Args:
            prefix: Cache key prefix
            *args: Additional key components

        Returns:
            Cache key string
        """
        key_parts = [prefix] + [str(arg) for arg in args]
        key = ":".join(key_parts)
        return f"chess_com:{key}"

    async def _get_cached(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve cached data from Redis.

        Args:
            cache_key: Redis cache key

        Returns:
            Cached data or None if not found/expired
        """
        if not self.redis_client or not settings.CACHE_ENABLED:
            return None

        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached)
            logger.debug(f"Cache miss: {cache_key}")
            return None
        except Exception as e:
            logger.warning(f"Cache get error for {cache_key}: {e}")
            return None

    async def _set_cached(self, cache_key: str, data: Any, ttl: int) -> None:
        """
        Store data in Redis cache.

        Args:
            cache_key: Redis cache key
            data: Data to cache (must be JSON serializable)
            ttl: Time to live in seconds
        """
        if not self.redis_client or not settings.CACHE_ENABLED:
            return

        try:
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(data, default=str),
            )
            logger.debug(f"Cached data: {cache_key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"Cache set error for {cache_key}: {e}")

    async def get_player_profile(self, username: str) -> PlayerProfile:
        """
        Fetch player profile information.

        Args:
            username: Chess.com username

        Returns:
            PlayerProfile model with user data

        Raises:
            UserNotFoundException: If username doesn't exist
            ChessComAPIException: For other API errors
        """
        username = username.lower().strip()
        cache_key = self._get_cache_key("profile", username)

        # Check cache first
        cached = await self._get_cached(cache_key)
        if cached:
            return PlayerProfile(**cached)

        # Fetch from API
        endpoint = f"player/{quote(username)}"
        data = await self._make_request(endpoint)

        # Parse and cache
        profile = PlayerProfile(**data)
        await self._set_cached(
            cache_key,
            profile.model_dump(mode="json"),
            self.CACHE_TTL_PROFILE,
        )

        logger.info(f"Fetched profile for user: {username}")
        return profile

    async def get_player_archives(self, username: str) -> List[str]:
        """
        Get list of available game archive URLs for a player.

        Args:
            username: Chess.com username

        Returns:
            List of archive URLs (month endpoints)

        Raises:
            UserNotFoundException: If username doesn't exist
            ChessComAPIException: For other API errors
        """
        username = username.lower().strip()
        cache_key = self._get_cache_key("archives", username)

        # Check cache
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        # Fetch from API
        endpoint = f"player/{quote(username)}/games/archives"
        data = await self._make_request(endpoint)

        archives = PlayerArchives(**data)
        archive_urls = [str(url) for url in archives.archives]

        # Cache for 12 hours
        await self._set_cached(cache_key, archive_urls, self.CACHE_TTL_GAMES)

        logger.info(f"Fetched {len(archive_urls)} archives for user: {username}")
        return archive_urls

    async def get_monthly_games(
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
            List of ChessGame models

        Raises:
            UserNotFoundException: If username doesn't exist
            ChessComAPIException: For other API errors
        """
        username = username.lower().strip()
        cache_key = self._get_cache_key("games", username, year, f"{month:02d}")

        # Check cache
        cached = await self._get_cached(cache_key)
        if cached:
            return [ChessGame(**game) for game in cached]

        # Fetch from API
        endpoint = f"player/{quote(username)}/games/{year}/{month:02d}"
        data = await self._make_request(endpoint)

        monthly_games = MonthlyGames(**data)
        games = monthly_games.games

        # Cache for 12 hours
        await self._set_cached(
            cache_key,
            [game.model_dump(mode="json") for game in games],
            self.CACHE_TTL_GAMES,
        )

        logger.info(f"Fetched {len(games)} games for {username} ({year}-{month:02d})")
        return games

    async def get_games_in_date_range(
        self,
        username: str,
        start_date: date,
        end_date: date,
        max_games: Optional[int] = None,
    ) -> List[ChessGame]:
        """
        Fetch all games within a date range.

        Args:
            username: Chess.com username
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            max_games: Maximum number of games to fetch (None for all)

        Returns:
            List of ChessGame models sorted by end_time (newest first)

        Raises:
            UserNotFoundException: If username doesn't exist
            NoGamesFoundException: If no games found in range
            ChessComAPIException: For other API errors
        """
        username = username.lower().strip()

        # Validate user exists
        await self.get_player_profile(username)

        # Generate list of (year, month) tuples to fetch
        months_to_fetch = []
        current = start_date.replace(day=1)
        end = end_date.replace(day=1)

        while current <= end:
            months_to_fetch.append((current.year, current.month))
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        logger.info(
            f"Fetching games for {username} from {start_date} to {end_date} "
            f"({len(months_to_fetch)} months)"
        )

        # Fetch games for each month (serially to avoid rate limits)
        all_games = []
        for year, month in months_to_fetch:
            try:
                games = await self.get_monthly_games(username, year, month)
                all_games.extend(games)

                # Check if we've reached max_games
                if max_games and len(all_games) >= max_games:
                    all_games = all_games[:max_games]
                    break

            except ChessComAPIException as e:
                # If a specific month returns 404, it might just be empty
                logger.warning(f"Could not fetch games for {year}-{month:02d}: {e}")
                continue

        # Filter games by actual date range
        start_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        end_timestamp = int(datetime.combine(end_date, datetime.max.time()).timestamp())

        filtered_games = [
            game
            for game in all_games
            if start_timestamp <= game.end_time <= end_timestamp
        ]

        # Sort by end_time descending (newest first)
        filtered_games.sort(key=lambda g: g.end_time, reverse=True)

        if not filtered_games:
            raise NoGamesFoundException(
                username,
                {"start_date": str(start_date), "end_date": str(end_date)},
            )

        logger.info(
            f"Found {len(filtered_games)} games for {username} in date range"
        )
        return filtered_games

    async def get_recent_games(
        self,
        username: str,
        count: int = 100,
        days: int = 90,
    ) -> List[ChessGame]:
        """
        Fetch recent games for a player.

        Args:
            username: Chess.com username
            count: Maximum number of games to fetch
            days: How many days back to search

        Returns:
            List of ChessGame models (up to count, newest first)

        Raises:
            UserNotFoundException: If username doesn't exist
            NoGamesFoundException: If no recent games found
            ChessComAPIException: For other API errors
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        games = await self.get_games_in_date_range(
            username,
            start_date,
            end_date,
            max_games=count,
        )

        return games[:count]

    async def close(self):
        """Close HTTP client connection."""
        if self._owned_client and self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Factory function for dependency injection
async def get_chess_com_client(
    redis_client: Optional[aioredis.Redis] = None,
) -> ChessComAPIClient:
    """
    Create and return a Chess.com API client instance.

    Args:
        redis_client: Optional Redis client for caching

    Returns:
        Configured ChessComAPIClient instance
    """
    client = ChessComAPIClient(redis_client=redis_client)
    await client.__aenter__()
    return client
