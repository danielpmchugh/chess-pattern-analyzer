"""
Chess game analysis API endpoints.

Provides endpoints for analyzing Chess.com games to identify patterns,
weaknesses, and provide improvement recommendations.
"""

from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional
from datetime import datetime

from app.services.chess_com import ChessComAPIClient
from app.engine.analysis_engine import PatternAnalysisEngine
from app.models.chess_models import EngineConfig
from app.config import settings
from app.core.logging import get_logger
from app.core.exceptions import (
    UserNotFoundException,
    NoGamesFoundException,
    ChessComAPIException,
)
from pydantic import BaseModel, Field

logger = get_logger(__name__)

router = APIRouter()


@router.get("/debug/{username}")
async def debug_games(username: str):
    """Debug endpoint to check what games are being fetched."""
    from datetime import date, timedelta
    import traceback

    try:
        async with ChessComAPIClient(redis_client=None) as client:
            # Check what dates we're using
            end_date = date.today()
            start_date = end_date - timedelta(days=90)

            logger.info(f"Fetching games from {start_date} to {end_date}")

            try:
                # Try to get monthly games directly
                year, month = end_date.year, end_date.month
                logger.info(f"Fetching monthly games for {year}-{month}")
                monthly_games = await client.get_monthly_games(username, year, month)

                logger.info(f"Got {len(monthly_games)} games for {year}-{month}")

                # Also try get_recent_games
                logger.info("Trying get_recent_games")
                recent_games = await client.get_recent_games(username=username, count=5)

                return {
                    "username": username,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "monthly_games_count": len(monthly_games),
                    "recent_games_count": len(recent_games),
                    "sample_monthly": [
                        {
                            "url": str(g.url),
                            "end_time": g.end_time,
                        }
                        for g in monthly_games[:2]
                    ],
                    "sample_recent": [
                        {
                            "url": str(g.url),
                            "end_time": g.end_time,
                        }
                        for g in recent_games[:2]
                    ],
                }
            except Exception as e:
                logger.error(f"Error in debug: {e}", exc_info=True)
                return {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                }
    except Exception as e:
        logger.error(f"Outer error in debug: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }


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
    "/analyze/{username}",
    response_model=AnalysisResponse,
    summary="Analyze Chess.com games",
    description="Analyze a player's recent Chess.com games to identify patterns and weaknesses",
)
async def analyze_player_games(
    username: str,
    games_limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Number of recent games to analyze (1-50)",
    ),
) -> AnalysisResponse:
    """
    Analyze a Chess.com player's recent games.

    This endpoint:
    1. Fetches recent games from Chess.com API
    2. Analyzes each game using Stockfish engine
    3. Detects common patterns and mistakes
    4. Provides personalized recommendations

    Args:
        username: Chess.com username
        games_limit: Number of recent games to analyze (1-50)

    Returns:
        AnalysisResponse with pattern counts and recommendations

    Raises:
        404: User not found or no games available
        500: Analysis error
    """
    logger.info(
        f"Starting analysis for user: {username}, games: {games_limit}"
    )

    try:
        # Fetch games from Chess.com (without Redis for now to simplify debugging)
        async with ChessComAPIClient(redis_client=None) as chess_client:
            try:
                games = await chess_client.get_recent_games(
                    username=username,
                    count=games_limit
                )
            except UserNotFoundException:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chess.com user '{username}' not found"
                )
            except NoGamesFoundException:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No games found for user '{username}'"
                )
            except ChessComAPIException as e:
                logger.error(f"Chess.com API error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Chess.com API temporarily unavailable"
                )

        if not games:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No games found for user '{username}'"
            )

        logger.info(f"Found {len(games)} games for {username}")

        # Initialize analysis engine
        engine_config = EngineConfig(
            path=settings.STOCKFISH_PATH,
            depth=settings.STOCKFISH_DEPTH,
            threads=settings.STOCKFISH_THREADS,
            hash_size=settings.STOCKFISH_HASH,
            time_limit=float(settings.STOCKFISH_TIMEOUT),
        )
        analysis_engine = PatternAnalysisEngine(config=engine_config)

        # Analyze games (limit concurrency to avoid overload)
        tactical_errors = 0
        opening_mistakes = 0
        time_pressure = 0
        positional_errors = 0
        endgame_mistakes = 0

        analyzed_count = 0

        # Analyze games sequentially to avoid overwhelming Stockfish
        for game in games:
            try:
                if not game.pgn:
                    logger.warning(f"Skipping game without PGN")
                    continue

                game_analysis = await analysis_engine.analyze_game(
                    pgn_text=game.pgn,
                    include_alternatives=False
                )

                # Aggregate pattern counts
                # Count blunders and mistakes as tactical errors
                tactical_errors += (
                    game_analysis.white_player.blunders +
                    game_analysis.white_player.mistakes +
                    game_analysis.black_player.blunders +
                    game_analysis.black_player.mistakes
                )

                # Count inaccuracies as positional errors
                positional_errors += (
                    game_analysis.white_player.inaccuracies +
                    game_analysis.black_player.inaccuracies
                )

                # Opening phase mistakes (first 10 moves)
                opening_phase_errors = sum(
                    1 for move in game_analysis.moves[:20]  # 10 moves each side
                    if move.classification in ["blunder", "mistake", "inaccuracy"]
                )
                opening_mistakes += opening_phase_errors

                # Endgame mistakes (identify by piece count or move number)
                endgame_phase_errors = sum(
                    1 for move in game_analysis.moves[-20:]  # Last 10 moves each side
                    if move.classification in ["blunder", "mistake"]
                )
                endgame_mistakes += endgame_phase_errors

                # Time pressure detection (simplified - could be enhanced)
                # For now, count quick games as time pressure
                if game.time_class in ["blitz", "bullet"]:
                    time_pressure += 1

                analyzed_count += 1

            except Exception as e:
                logger.warning(f"Failed to analyze game: {e}")
                continue

        if analyzed_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to analyze any games"
            )

        # Generate recommendations
        recommendations = _generate_recommendations(
            tactical_errors=tactical_errors,
            opening_mistakes=opening_mistakes,
            time_pressure=time_pressure,
            positional_errors=positional_errors,
            endgame_mistakes=endgame_mistakes,
            total_games=analyzed_count,
        )

        logger.info(f"Analysis complete for {username}: {analyzed_count} games analyzed")

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
        logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during analysis"
        )


def _generate_recommendations(
    tactical_errors: int,
    opening_mistakes: int,
    time_pressure: int,
    positional_errors: int,
    endgame_mistakes: int,
    total_games: int,
) -> list[str]:
    """
    Generate personalized recommendations based on detected patterns.

    Args:
        tactical_errors: Number of tactical mistakes
        opening_mistakes: Number of opening errors
        time_pressure: Number of time pressure issues
        positional_errors: Number of positional mistakes
        endgame_mistakes: Number of endgame errors
        total_games: Total number of games analyzed

    Returns:
        List of personalized recommendations
    """
    recommendations = []

    # Normalize per game
    tactical_per_game = tactical_errors / max(total_games, 1)
    opening_per_game = opening_mistakes / max(total_games, 1)
    positional_per_game = positional_errors / max(total_games, 1)
    endgame_per_game = endgame_mistakes / max(total_games, 1)

    # Prioritize recommendations by severity
    if tactical_per_game > 3:
        recommendations.append(
            "Focus on tactical training - you're making frequent tactical mistakes. "
            "Practice tactical puzzles daily on Chess.com or Lichess."
        )

    if opening_per_game > 2:
        recommendations.append(
            "Study opening theory for your preferred openings. "
            "Your opening phase shows room for improvement."
        )

    if positional_per_game > 2:
        recommendations.append(
            "Work on positional understanding - study master games and learn common "
            "positional concepts like weak squares, pawn structure, and piece activity."
        )

    if endgame_per_game > 1:
        recommendations.append(
            "Practice endgame fundamentals - your endgame technique needs work. "
            "Study basic endgames like king and pawn, rook endgames, and basic checkmates."
        )

    if time_pressure > total_games * 0.5:
        recommendations.append(
            "Improve time management - you're playing too many games under time pressure. "
            "Consider playing longer time controls to reduce time pressure mistakes."
        )

    # Always include at least one recommendation
    if not recommendations:
        recommendations.append(
            "Keep playing and analyzing your games! Focus on learning from your mistakes "
            "and studying master games in your opening repertoire."
        )

    return recommendations[:5]  # Limit to top 5 recommendations
