"""
Simplified analysis endpoint for MVP.

This endpoint provides a working analysis without the full engine
to get the frontend functional while we debug the complex analysis.
"""

from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, Field

from app.services.chess_com import ChessComAPIClient
from app.core.logging import get_logger
from app.core.exceptions import (
    UserNotFoundException,
    NoGamesFoundException,
    ChessComAPIException,
)

logger = get_logger(__name__)

router = APIRouter()


class PatternCounts(BaseModel):
    """Aggregated pattern detection counts."""

    tactical_errors: int = Field(0, description="Number of tactical mistakes")
    opening_mistakes: int = Field(0, description="Number of opening errors")
    time_pressure: int = Field(0, description="Number of moves made under time pressure")
    positional_errors: int = Field(0, description="Number of positional mistakes")
    endgame_mistakes: int = Field(0, description="Number of endgame errors")


class AnalysisResponse(BaseModel):
    """Response model for game analysis."""

    username: str = Field(..., description="Chess.com username")
    total_games: int = Field(..., description="Number of games analyzed")
    patterns: PatternCounts = Field(..., description="Detected error patterns")
    recommendations: list[str] = Field(..., description="Personalized improvement recommendations")
    analysis_date: datetime = Field(..., description="When analysis was performed")


@router.get(
    "/simple-analyze/{username}",
    response_model=AnalysisResponse,
    summary="Simple Chess.com game analysis (MVP)",
    description="Simplified analysis that works without full Stockfish engine",
)
async def simple_analyze_player_games(
    username: str,
    games_limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Number of recent games to analyze (1-50)",
    ),
) -> AnalysisResponse:
    """
    Simplified analysis endpoint that fetches games and provides basic pattern detection.

    This MVP version:
    - Fetches recent games from current month
    - Provides simplified pattern detection
    - Returns quickly without full engine analysis
    """
    logger.info(f"Simple analysis for {username}, limit: {games_limit}")

    try:
        async with ChessComAPIClient(redis_client=None) as chess_client:
            # Fetch just the current month's games (which we know works)
            today = date.today()
            try:
                monthly_games = await chess_client.get_monthly_games(
                    username=username,
                    year=today.year,
                    month=today.month
                )
            except UserNotFoundException:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chess.com user '{username}' not found"
                )
            except ChessComAPIException as e:
                logger.error(f"Chess.com API error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Chess.com API temporarily unavailable"
                )

            if not monthly_games:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No games found for user '{username}' this month"
                )

            # Limit to requested number
            games_to_analyze = monthly_games[:games_limit]
            analyzed_count = len(games_to_analyze)

            logger.info(f"Analyzing {analyzed_count} games for {username}")

            # Simplified pattern detection based on game metadata
            tactical_errors = 0
            opening_mistakes = 0
            time_pressure = 0
            positional_errors = 0
            endgame_mistakes = 0

            for game in games_to_analyze:
                # Simple heuristics based on time control and game type
                if game.time_class == "bullet":
                    time_pressure += 2  # Bullet = high time pressure
                    tactical_errors += 1
                elif game.time_class == "blitz":
                    time_pressure += 1
                    tactical_errors += 1

                # Estimate errors based on rating and result
                # In a real implementation, this would use Stockfish
                opening_mistakes += 1  # Simplified: assume 1 per game
                positional_errors += 2  # Simplified: assume 2 per game
                endgame_mistakes += 1  # Simplified: assume 1 per game

            # Generate recommendations
            recommendations = _generate_simple_recommendations(
                tactical_errors=tactical_errors,
                opening_mistakes=opening_mistakes,
                time_pressure=time_pressure,
                positional_errors=positional_errors,
                endgame_mistakes=endgame_mistakes,
                total_games=analyzed_count,
            )

            return AnalysisResponse(
                username=username,
                total_games=analyzed_count,
                patterns=PatternCounts(
                    tactical_errors=tactical_errors,
                    opening_mistakes=opening_mistakes,
                    time_pressure=time_pressure,
                    positional_errors=positional_errors,
                    endgame_mistakes=endgame_mistakes,
                ),
                recommendations=recommendations,
                analysis_date=datetime.utcnow(),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during analysis"
        )


def _generate_simple_recommendations(
    tactical_errors: int,
    opening_mistakes: int,
    time_pressure: int,
    positional_errors: int,
    endgame_mistakes: int,
    total_games: int,
) -> list[str]:
    """Generate simplified recommendations."""
    recommendations = []

    # Normalize per game
    tactical_per_game = tactical_errors / max(total_games, 1)
    time_pressure_per_game = time_pressure / max(total_games, 1)

    if time_pressure_per_game > 1:
        recommendations.append(
            "Consider playing longer time controls to reduce time pressure mistakes. "
            "Your bullet/blitz games show signs of time management issues."
        )

    if tactical_per_game > 1:
        recommendations.append(
            "Focus on tactical training - practice daily puzzles on Chess.com or Lichess "
            "to improve pattern recognition and reduce blunders."
        )

    recommendations.append(
        "Study opening theory for your most-played openings. "
        "Consistent opening preparation reduces early-game mistakes."
    )

    recommendations.append(
        "Practice endgame fundamentals - many games are decided in the endgame. "
        "Study basic endgames like king and pawn, and rook endgames."
        )

    recommendations.append(
        "Analyze your games with an engine after playing to identify patterns in your mistakes. "
        "Chess.com's game review feature is great for this!"
    )

    return recommendations[:5]
