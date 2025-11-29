"""
Pydantic models for Chess.com API data structures.

This module defines the data models for Chess.com Published-Data API
responses, providing type safety and automatic validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, field_validator


class PlayerProfile(BaseModel):
    """Chess.com player profile information."""

    username: str = Field(..., description="Chess.com username")
    player_id: int = Field(..., description="Numeric player ID")
    url: HttpUrl = Field(..., description="Profile URL")
    name: Optional[str] = Field(None, description="Real name")
    avatar: Optional[HttpUrl] = Field(None, description="Avatar URL")
    followers: int = Field(default=0, description="Number of followers")
    country: Optional[str] = Field(None, description="Country URL")
    location: Optional[str] = Field(None, description="Location string")
    last_online: int = Field(..., description="Last online timestamp")
    joined: int = Field(..., description="Join date timestamp")
    status: str = Field(..., description="Account status")
    is_streamer: bool = Field(default=False, description="Streamer status")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "username": "hikaru",
                "player_id": 32772895,
                "url": "https://www.chess.com/member/hikaru",
                "name": "Hikaru Nakamura",
                "followers": 50000,
                "last_online": 1700000000,
                "joined": 1400000000,
                "status": "premium",
                "is_streamer": True,
            }
        }


class PlayerStats(BaseModel):
    """Player rating in a specific time control."""

    rating: int = Field(..., description="Current rating")
    date: Optional[int] = Field(None, description="Last game timestamp")
    rd: Optional[int] = Field(None, description="Rating deviation")

    class Config:
        populate_by_name = True


class GamePlayer(BaseModel):
    """Player information within a game."""

    username: str = Field(..., description="Player username")
    rating: int = Field(..., description="Player rating")
    result: str = Field(..., description="Game result for this player")
    uuid: str = Field(..., alias="@id", description="Player UUID")

    class Config:
        populate_by_name = True


class ChessGame(BaseModel):
    """Chess.com game data."""

    url: HttpUrl = Field(..., description="Game URL")
    pgn: str = Field(..., description="PGN notation of the game")
    time_control: str = Field(..., description="Time control format")
    end_time: int = Field(..., description="Game end timestamp")
    rated: bool = Field(..., description="Whether game is rated")
    tcn: Optional[str] = Field(None, description="TCN notation")
    uuid: str = Field(..., description="Unique game identifier")
    initial_setup: Optional[str] = Field(None, description="Initial FEN position")
    fen: Optional[str] = Field(None, description="Final FEN position")
    time_class: str = Field(..., description="Time class (rapid, blitz, bullet)")
    rules: str = Field(..., description="Game variant rules")

    # Player information
    white: GamePlayer = Field(..., description="White player data")
    black: GamePlayer = Field(..., description="Black player data")

    # Tournament information (optional)
    tournament: Optional[HttpUrl] = Field(None, description="Tournament URL")
    match: Optional[HttpUrl] = Field(None, description="Match URL")

    @field_validator("pgn")
    @classmethod
    def validate_pgn(cls, v: str) -> str:
        """Ensure PGN is not empty."""
        if not v or not v.strip():
            raise ValueError("PGN data cannot be empty")
        return v

    @field_validator("time_control")
    @classmethod
    def validate_time_control(cls, v: str) -> str:
        """Validate time control format."""
        if not v or not isinstance(v, str):
            raise ValueError("Time control must be a valid string")
        return v

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "url": "https://www.chess.com/game/live/12345678",
                "pgn": '[Event "Live Chess"]\n[Site "Chess.com"]\n...',
                "time_control": "600",
                "end_time": 1700000000,
                "rated": True,
                "uuid": "abc-def-123",
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
        }


class MonthlyGames(BaseModel):
    """Response from the monthly games endpoint."""

    games: List[ChessGame] = Field(default_factory=list, description="List of games")

    class Config:
        json_schema_extra = {
            "example": {
                "games": []
            }
        }


class PlayerArchives(BaseModel):
    """Response from player archives endpoint."""

    archives: List[HttpUrl] = Field(..., description="List of archive URLs")

    class Config:
        json_schema_extra = {
            "example": {
                "archives": [
                    "https://api.chess.com/pub/player/hikaru/games/2024/01",
                    "https://api.chess.com/pub/player/hikaru/games/2024/02",
                ]
            }
        }


class ParsedGame(BaseModel):
    """Parsed and normalized game data ready for analysis."""

    game_id: str = Field(..., description="Unique game identifier")
    url: str = Field(..., description="Game URL")
    pgn: str = Field(..., description="PGN notation")

    # Time control
    time_control: str = Field(..., description="Original time control")
    time_class: str = Field(..., description="Time class category")

    # Game metadata
    rated: bool = Field(..., description="Rated game flag")
    variant: str = Field(default="chess", description="Chess variant")
    end_time: datetime = Field(..., description="Game end time")

    # Players
    white_username: str = Field(..., description="White player username")
    white_rating: int = Field(..., description="White player rating")
    white_result: str = Field(..., description="White player result")

    black_username: str = Field(..., description="Black player username")
    black_rating: int = Field(..., description="Black player rating")
    black_result: str = Field(..., description="Black player result")

    # Tournament (optional)
    tournament_url: Optional[str] = Field(None, description="Tournament URL")

    # Parsed PGN data
    moves: List[str] = Field(default_factory=list, description="List of moves in SAN")
    move_count: int = Field(..., description="Total number of moves")

    class Config:
        json_schema_extra = {
            "example": {
                "game_id": "abc-def-123",
                "url": "https://www.chess.com/game/live/12345678",
                "pgn": "[Event \"Live Chess\"]...",
                "time_control": "600",
                "time_class": "rapid",
                "rated": True,
                "variant": "chess",
                "end_time": "2024-01-15T10:30:00Z",
                "white_username": "player1",
                "white_rating": 1500,
                "white_result": "win",
                "black_username": "player2",
                "black_rating": 1480,
                "black_result": "checkmated",
                "moves": ["e4", "e5", "Nf3"],
                "move_count": 45,
            }
        }
