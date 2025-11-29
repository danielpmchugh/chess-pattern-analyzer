"""
Chess analysis data models.

Pydantic models for chess game analysis, pattern detection, and evaluations.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class MoveClassification(str, Enum):
    """Classification of move quality."""
    BRILLIANT = "brilliant"
    BEST = "best"
    GOOD = "good"
    BOOK = "book"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"
    CRITICAL_BLUNDER = "critical_blunder"


class PatternType(str, Enum):
    """Types of chess patterns detected."""
    HANGING_PIECE = "hanging_piece"
    FORK = "fork"
    PIN = "pin"
    SKEWER = "skewer"
    DISCOVERED_ATTACK = "discovered_attack"
    BACK_RANK_WEAKNESS = "back_rank_weakness"
    KNIGHT_FORK = "knight_fork"
    MISSED_CHECKMATE = "missed_checkmate"
    ALLOWS_TACTIC = "allows_tactic"
    POSITIONAL_BLUNDER = "positional_blunder"
    TRAPPED_PIECE = "trapped_piece"
    WEAK_PAWN_STRUCTURE = "weak_pawn_structure"


class BlunderType(str, Enum):
    """Specific types of blunders."""
    HANGING_PIECE = "hanging_piece"
    MISSED_CHECKMATE = "missed_checkmate"
    ALLOWS_TACTIC = "allows_tactic"
    POSITIONAL_BLUNDER = "positional_blunder"
    TIME_PRESSURE = "time_pressure"
    OPENING_MISTAKE = "opening_mistake"
    ENDGAME_TECHNIQUE = "endgame_technique"
    UNSPECIFIED = "unspecified"


class PositionEvaluation(BaseModel):
    """Chess position evaluation from engine."""
    centipawns: Optional[int] = Field(None, description="Evaluation in centipawns")
    mate_in: Optional[int] = Field(None, description="Mate in N moves (positive for player to move)")
    depth: int = Field(..., description="Search depth")
    best_move: Optional[str] = Field(None, description="Best move in UCI notation")

    @field_validator('centipawns')
    @classmethod
    def validate_centipawns(cls, v):
        """Validate centipawn values are reasonable."""
        if v is not None and abs(v) > 20000:
            raise ValueError("Centipawn evaluation out of reasonable range")
        return v


class AlternativeMove(BaseModel):
    """Alternative move suggestion."""
    move: str = Field(..., description="Move in UCI notation")
    san: str = Field(..., description="Move in SAN notation")
    evaluation: PositionEvaluation
    description: Optional[str] = Field(None, description="Human-readable explanation")


class TacticalPattern(BaseModel):
    """Detected tactical pattern in position."""
    pattern_type: PatternType
    severity: str = Field(..., description="high, medium, low")
    pieces_involved: List[str] = Field(default_factory=list, description="Pieces involved in pattern")
    squares: List[str] = Field(default_factory=list, description="Key squares in pattern")
    description: Optional[str] = Field(None, description="Human-readable description")
    centipawn_value: Optional[int] = Field(None, description="Material value involved")


class MoveAnalysis(BaseModel):
    """Analysis of a single move."""
    move_number: int = Field(..., description="Full move number (1, 2, 3...)")
    half_move: int = Field(..., description="Half-move ply")
    color: str = Field(..., description="white or black")
    move: str = Field(..., description="Move in UCI notation")
    san: str = Field(..., description="Move in SAN (algebraic) notation")

    classification: MoveClassification
    eval_before: Optional[int] = Field(None, description="Evaluation before move (centipawns)")
    eval_after: Optional[int] = Field(None, description="Evaluation after move (centipawns)")
    best_move: Optional[str] = Field(None, description="Engine's best move (UCI)")
    best_move_san: Optional[str] = Field(None, description="Engine's best move (SAN)")
    best_eval: Optional[int] = Field(None, description="Evaluation of best move")
    eval_loss: int = Field(0, description="Centipawn loss from best move")

    blunder_type: Optional[BlunderType] = None
    tactical_patterns: List[TacticalPattern] = Field(default_factory=list)
    alternatives: List[AlternativeMove] = Field(default_factory=list, max_length=3)

    time_spent: Optional[float] = Field(None, description="Time spent on move (seconds)")
    time_remaining: Optional[float] = Field(None, description="Time remaining after move (seconds)")

    position_fen: str = Field(..., description="FEN after this move")


class OpeningInfo(BaseModel):
    """Opening information and analysis."""
    eco: str = Field(..., description="ECO code (A00-E99)")
    name: str = Field(..., description="Opening name")
    moves: List[str] = Field(default_factory=list, description="Opening moves in SAN")
    moves_uci: List[str] = Field(default_factory=list, description="Opening moves in UCI")
    deviation_move: Optional[int] = Field(None, description="Move number where theory was left")
    mistakes_in_opening: List[MoveAnalysis] = Field(default_factory=list)
    opening_accuracy: Optional[float] = Field(None, description="Accuracy in opening phase (0-100)")


class CriticalMoment(BaseModel):
    """A critical moment in the game."""
    move_number: int
    half_move: int
    description: str
    evaluation_swing: int = Field(..., description="Centipawn swing")
    missed_opportunity: bool = Field(False, description="Was this a missed win/advantage?")


class GamePhaseStats(BaseModel):
    """Statistics for a game phase."""
    phase: str = Field(..., description="opening, middlegame, endgame")
    move_count: int
    accuracy: float = Field(..., ge=0, le=100)
    blunders: int
    mistakes: int
    inaccuracies: int
    avg_centipawn_loss: float


class PlayerAnalysis(BaseModel):
    """Analysis for one player in the game."""
    username: str
    color: str = Field(..., description="white or black")
    rating: Optional[int] = None

    accuracy: float = Field(..., ge=0, le=100, description="Overall accuracy (0-100)")
    avg_centipawn_loss: float = Field(..., description="Average centipawn loss per move")

    brilliant_moves: int = Field(0, ge=0)
    best_moves: int = Field(0, ge=0)
    good_moves: int = Field(0, ge=0)
    inaccuracies: int = Field(0, ge=0)
    mistakes: int = Field(0, ge=0)
    blunders: int = Field(0, ge=0)

    patterns_detected: List[PatternType] = Field(default_factory=list)
    opening_phase: Optional[GamePhaseStats] = None
    middlegame_phase: Optional[GamePhaseStats] = None
    endgame_phase: Optional[GamePhaseStats] = None

    time_management_score: Optional[float] = Field(None, ge=0, le=100)
    critical_moments: List[CriticalMoment] = Field(default_factory=list)


class GameAnalysis(BaseModel):
    """Complete game analysis result."""
    game_id: str = Field(..., description="Unique game identifier")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    # Game metadata
    white_player: str
    black_player: str
    white_rating: Optional[int] = None
    black_rating: Optional[int] = None
    result: str = Field(..., description="1-0, 0-1, 1/2-1/2")
    time_control: Optional[str] = None

    # Opening analysis
    opening: OpeningInfo

    # Move-by-move analysis
    moves: List[MoveAnalysis] = Field(default_factory=list)
    total_moves: int = Field(..., ge=0)

    # Player analyses
    white_analysis: PlayerAnalysis
    black_analysis: PlayerAnalysis

    # Game-wide patterns
    all_patterns_detected: List[PatternType] = Field(default_factory=list)
    critical_moments: List[CriticalMoment] = Field(default_factory=list)

    # Performance metrics
    analysis_time_seconds: float = Field(..., description="Time taken to analyze game")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PatternSummary(BaseModel):
    """Summary of pattern occurrences across games."""
    pattern_type: PatternType
    frequency: int = Field(..., ge=0, description="Number of occurrences")
    avg_centipawn_loss: float = Field(..., description="Average centipawn impact")
    severity_score: float = Field(..., description="Frequency * avg_centipawn_loss")
    examples: List[Dict[str, Any]] = Field(default_factory=list, max_length=5)
    games_affected: int = Field(..., ge=0, description="Number of games with this pattern")


class WeaknessAnalysis(BaseModel):
    """Analysis of player weaknesses across multiple games."""
    username: str
    games_analyzed: int = Field(..., ge=1)
    date_range_start: datetime
    date_range_end: datetime

    # Overall statistics
    overall_accuracy: float = Field(..., ge=0, le=100)
    total_games: int
    wins: int
    losses: int
    draws: int

    # Top patterns/weaknesses
    top_patterns: List[PatternSummary] = Field(max_length=10)

    # Phase-specific weaknesses
    opening_accuracy: float = Field(..., ge=0, le=100)
    middlegame_accuracy: float = Field(..., ge=0, le=100)
    endgame_accuracy: float = Field(..., ge=0, le=100)

    # Error distribution
    total_blunders: int
    total_mistakes: int
    total_inaccuracies: int

    # Time management
    time_pressure_blunders: int = Field(0, description="Blunders in time pressure")
    time_management_score: Optional[float] = Field(None, ge=0, le=100)

    # Recommendations
    primary_weakness: Optional[PatternType] = None
    secondary_weakness: Optional[PatternType] = None
    recommended_focus_areas: List[str] = Field(default_factory=list, max_length=5)


class EngineConfig(BaseModel):
    """Stockfish engine configuration."""
    path: str = Field(default="/usr/local/bin/stockfish", description="Path to Stockfish binary")
    depth: int = Field(default=18, ge=10, le=30, description="Analysis depth")
    time_limit: float = Field(default=0.5, ge=0.1, le=10.0, description="Seconds per position")
    threads: int = Field(default=2, ge=1, le=8, description="CPU threads")
    hash_size: int = Field(default=128, ge=16, le=1024, description="Hash table size (MB)")
    multipv: int = Field(default=3, ge=1, le=5, description="Number of principal variations")


class AnalysisRequest(BaseModel):
    """Request to analyze game(s)."""
    username: str = Field(..., min_length=3, max_length=50)
    pgn_text: Optional[str] = Field(None, description="Single PGN to analyze")
    game_ids: Optional[List[str]] = Field(None, description="List of game IDs to analyze")
    include_alternatives: bool = Field(default=True, description="Include alternative move suggestions")
    engine_depth: Optional[int] = Field(None, ge=10, le=25, description="Override default engine depth")


class AnalysisResponse(BaseModel):
    """Response from analysis endpoint."""
    success: bool
    game_analysis: Optional[GameAnalysis] = None
    batch_analyses: Optional[List[GameAnalysis]] = Field(None, description="For batch requests")
    message: Optional[str] = None
    analysis_time_seconds: float
