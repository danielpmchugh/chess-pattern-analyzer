"""
Game data models for Chess.com API responses.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class GameResult(str, Enum):
    """Possible game results."""
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    ABANDONED = "abandoned"
    TIMEOUT = "timeout"
    RESIGNED = "resigned"
    STALEMATE = "stalemate"
    CHECKMATE = "checkmate"
    REPETITION = "repetition"
    INSUFFICIENT_MATERIAL = "insufficient"
    FIFTY_MOVE = "50move"
    TIMEVSINSUFFICIENT = "timevsinsufficient"
    AGREED = "agreed"


class PlayerColor(str, Enum):
    """Chess player colors."""
    WHITE = "white"
    BLACK = "black"


class PlayerInfo(BaseModel):
    """Player information in a game."""
    username: str
    rating: int
    result: str
    uuid: Optional[str] = None

    @field_validator('username')
    @classmethod
    def username_lowercase(cls, v: str) -> str:
        """Convert username to lowercase for consistency."""
        return v.lower()


class ChessGame(BaseModel):
    """Chess game from Chess.com API."""
    url: str
    pgn: str
    time_control: str
    end_time: int  # Unix timestamp
    rated: bool

    # Player information
    white: PlayerInfo
    black: PlayerInfo

    # Optional fields
    uuid: Optional[str] = None
    initial_setup: Optional[str] = None
    fen: Optional[str] = None
    time_class: Optional[str] = None
    rules: Optional[str] = None
    tournament: Optional[str] = None
    match: Optional[str] = None

    @property
    def end_datetime(self) -> datetime:
        """Convert end_time to datetime."""
        return datetime.fromtimestamp(self.end_time)

    @property
    def game_id(self) -> str:
        """Extract game ID from URL."""
        return self.url.split('/')[-1]

    def get_player_result(self, username: str) -> Optional[str]:
        """Get the result for a specific player."""
        username = username.lower()
        if self.white.username == username:
            return self.white.result
        elif self.black.username == username:
            return self.black.result
        return None

    def get_player_rating(self, username: str) -> Optional[int]:
        """Get the rating for a specific player."""
        username = username.lower()
        if self.white.username == username:
            return self.white.rating
        elif self.black.username == username:
            return self.black.rating
        return None

    def get_player_color(self, username: str) -> Optional[PlayerColor]:
        """Get the color for a specific player."""
        username = username.lower()
        if self.white.username == username:
            return PlayerColor.WHITE
        elif self.black.username == username:
            return PlayerColor.BLACK
        return None

    def get_opponent_username(self, username: str) -> Optional[str]:
        """Get opponent's username."""
        username = username.lower()
        if self.white.username == username:
            return self.black.username
        elif self.black.username == username:
            return self.white.username
        return None


class PlayerProfile(BaseModel):
    """Chess.com player profile."""
    username: str
    player_id: int = Field(alias="@id")
    url: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    followers: Optional[int] = None
    country: Optional[str] = None
    location: Optional[str] = None
    last_online: Optional[int] = None
    joined: Optional[int] = None
    status: Optional[str] = None
    is_streamer: Optional[bool] = None
    twitch_url: Optional[str] = None

    model_config = {"populate_by_name": True}

    @field_validator('username')
    @classmethod
    def username_lowercase(cls, v: str) -> str:
        """Convert username to lowercase."""
        return v.lower()

    @property
    def joined_datetime(self) -> Optional[datetime]:
        """Convert joined timestamp to datetime."""
        return datetime.fromtimestamp(self.joined) if self.joined else None

    @property
    def last_online_datetime(self) -> Optional[datetime]:
        """Convert last_online timestamp to datetime."""
        return datetime.fromtimestamp(self.last_online) if self.last_online else None


class PlayerStats(BaseModel):
    """Chess.com player statistics."""
    chess_rapid: Optional[Dict[str, Any]] = None
    chess_blitz: Optional[Dict[str, Any]] = None
    chess_bullet: Optional[Dict[str, Any]] = None
    chess_daily: Optional[Dict[str, Any]] = None
    tactics: Optional[Dict[str, Any]] = None
    lessons: Optional[Dict[str, Any]] = None
    puzzle_rush: Optional[Dict[str, Any]] = None

    def get_rating(self, time_class: str) -> Optional[int]:
        """Get current rating for a time class."""
        time_class_map = {
            "rapid": self.chess_rapid,
            "blitz": self.chess_blitz,
            "bullet": self.chess_bullet,
            "daily": self.chess_daily,
        }

        stats = time_class_map.get(time_class)
        if stats and "last" in stats:
            return stats["last"].get("rating")
        return None


class MonthlyGamesArchive(BaseModel):
    """Monthly games archive URL."""
    games: list[ChessGame]


class GamesArchiveList(BaseModel):
    """List of available game archives for a player."""
    archives: list[str]

    def get_recent_archives(self, count: int = 3) -> list[str]:
        """Get the N most recent archive URLs."""
        return sorted(self.archives, reverse=True)[:count]
