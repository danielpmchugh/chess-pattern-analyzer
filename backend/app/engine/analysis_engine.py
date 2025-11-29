"""
Main pattern analysis orchestrator.

Coordinates all analysis components (Stockfish, pattern detection, opening analysis,
blunder detection) to produce complete game analyses.
"""

import asyncio
import chess
import chess.pgn
import io
import time
from datetime import datetime
from typing import List, Optional, Callable
from collections import Counter

from app.models.chess_models import (
    EngineConfig,
    GameAnalysis,
    PlayerAnalysis,
    CriticalMoment,
    GamePhaseStats,
    PatternType,
    MoveAnalysis,
)
from app.engine.stockfish_manager import StockfishManager
from app.engine.pattern_detector import TacticalPatternDetector
from app.engine.opening_analyzer import OpeningAnalyzer
from app.engine.blunder_detector import BlunderDetector


class PatternAnalysisEngine:
    """
    Main chess analysis engine.

    Orchestrates all components to analyze chess games:
    - Stockfish position evaluation
    - Tactical pattern detection
    - Opening classification
    - Move classification (blunders, mistakes, inaccuracies)
    - Player accuracy calculation
    - Critical moment identification
    """

    def __init__(self, config: EngineConfig):
        """
        Initialize analysis engine.

        Args:
            config: Stockfish engine configuration
        """
        self.config = config
        self.tactical_detector = TacticalPatternDetector()
        self.opening_analyzer = OpeningAnalyzer()
        self.blunder_detector = BlunderDetector()

    async def analyze_game(
        self,
        pgn_text: str,
        include_alternatives: bool = True,
    ) -> GameAnalysis:
        """
        Analyze a complete chess game.

        Args:
            pgn_text: PGN string of the game
            include_alternatives: Include alternative move suggestions

        Returns:
            Complete game analysis

        Raises:
            ValueError: If PGN is invalid
        """
        start_time = time.time()

        # Parse PGN
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)

        if not game:
            raise ValueError("Invalid PGN format")

        # Extract game metadata
        headers = game.headers
        white_player = headers.get("White", "Unknown")
        black_player = headers.get("Black", "Unknown")
        white_rating = self._parse_rating(headers.get("WhiteElo"))
        black_rating = self._parse_rating(headers.get("BlackElo"))
        result = headers.get("Result", "*")
        time_control = headers.get("TimeControl")

        # Generate game ID from PGN
        game_id = self._generate_game_id(pgn_text)

        # Start engine
        async with StockfishManager(self.config) as engine:
            # Analyze all moves
            moves_analysis, moves_uci = await self._analyze_all_moves(
                game,
                engine,
                include_alternatives
            )

            # Analyze opening
            opening_info = await self.opening_analyzer.analyze_opening(
                moves_uci,
                moves_analysis
            )

            # Detect patterns in all moves
            all_patterns = []
            for i, move_analysis in enumerate(moves_analysis):
                board = self._get_board_at_position(game, i + 1)
                if board:
                    patterns = self.tactical_detector.detect_all_patterns(
                        board,
                        chess.Move.from_uci(move_analysis.move) if move_analysis.move else None
                    )
                    move_analysis.tactical_patterns = patterns
                    all_patterns.extend(patterns)

            # Identify critical moments
            critical_moments = self._identify_critical_moments(moves_analysis)

            # Calculate player statistics
            white_analysis = self._analyze_player(
                moves_analysis,
                "white",
                white_player,
                white_rating,
                critical_moments
            )

            black_analysis = self._analyze_player(
                moves_analysis,
                "black",
                black_player,
                black_rating,
                critical_moments
            )

            # Get all unique pattern types detected
            all_pattern_types = list(set(p.pattern_type for p in all_patterns))

        analysis_time = time.time() - start_time

        return GameAnalysis(
            game_id=game_id,
            analyzed_at=datetime.utcnow(),
            white_player=white_player,
            black_player=black_player,
            white_rating=white_rating,
            black_rating=black_rating,
            result=result,
            time_control=time_control,
            opening=opening_info,
            moves=moves_analysis,
            total_moves=len(moves_analysis),
            white_analysis=white_analysis,
            black_analysis=black_analysis,
            all_patterns_detected=all_pattern_types,
            critical_moments=critical_moments,
            analysis_time_seconds=round(analysis_time, 2)
        )

    async def analyze_batch(
        self,
        pgn_texts: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[GameAnalysis]:
        """
        Analyze multiple games in batch.

        Args:
            pgn_texts: List of PGN strings
            progress_callback: Optional callback(current, total)

        Returns:
            List of game analyses
        """
        analyses = []

        for i, pgn_text in enumerate(pgn_texts):
            try:
                analysis = await self.analyze_game(pgn_text, include_alternatives=False)
                analyses.append(analysis)

                if progress_callback:
                    progress_callback(i + 1, len(pgn_texts))

            except Exception as e:
                # Log error but continue with other games
                print(f"Failed to analyze game {i+1}: {e}")
                continue

        return analyses

    async def _analyze_all_moves(
        self,
        game: chess.pgn.Game,
        engine: StockfishManager,
        include_alternatives: bool,
    ) -> tuple[List[MoveAnalysis], List[str]]:
        """
        Analyze all moves in the game.

        Args:
            game: Parsed PGN game
            engine: Stockfish manager
            include_alternatives: Include alternative moves

        Returns:
            Tuple of (move analyses, moves in UCI)
        """
        moves_analysis = []
        moves_uci = []

        board = game.board()
        node = game
        move_number = 1
        half_move = 0

        while node.variations:
            next_node = node.variation(0)
            move = next_node.move

            # Extract time information if available
            comment = next_node.comment
            time_spent, time_remaining = self._parse_time_from_comment(comment)

            # Analyze the move
            move_analysis = await self.blunder_detector.analyze_move(
                board_before=board,
                move=move,
                engine=engine,
                move_number=move_number,
                half_move=half_move,
                time_spent=time_spent,
                time_remaining=time_remaining,
            )

            # Limit alternatives if not requested
            if not include_alternatives:
                move_analysis.alternatives = []

            moves_analysis.append(move_analysis)
            moves_uci.append(move.uci())

            # Advance board
            board.push(move)
            half_move += 1

            # Increment full move number after black's move
            if board.turn == chess.WHITE:
                move_number += 1

            node = next_node

        return moves_analysis, moves_uci

    def _identify_critical_moments(
        self,
        moves_analysis: List[MoveAnalysis]
    ) -> List[CriticalMoment]:
        """
        Identify critical moments in the game.

        Critical moments are:
        - Large evaluation swings (> 200cp)
        - Blunders that changed game outcome
        - Missed winning chances

        Args:
            moves_analysis: All move analyses

        Returns:
            List of critical moments
        """
        critical_moments = []

        for i, move in enumerate(moves_analysis):
            # Check for large eval swing
            if move.eval_loss and move.eval_loss > 200:
                # Check if this changed the game outcome
                was_winning = move.eval_before and move.eval_before > 150
                now_losing = move.eval_after and move.eval_after < -150

                critical_moments.append(CriticalMoment(
                    move_number=move.move_number,
                    half_move=move.half_move,
                    description=f"{move.color.capitalize()} blundered: {move.san}",
                    evaluation_swing=move.eval_loss,
                    missed_opportunity=was_winning and now_losing,
                ))

            # Check for missed checkmate
            if move.blunder_type and move.blunder_type.value == "missed_checkmate":
                critical_moments.append(CriticalMoment(
                    move_number=move.move_number,
                    half_move=move.half_move,
                    description=f"{move.color.capitalize()} missed checkmate",
                    evaluation_swing=1000,
                    missed_opportunity=True,
                ))

        return critical_moments

    def _analyze_player(
        self,
        moves_analysis: List[MoveAnalysis],
        color: str,
        username: str,
        rating: Optional[int],
        critical_moments: List[CriticalMoment],
    ) -> PlayerAnalysis:
        """
        Analyze performance of one player.

        Args:
            moves_analysis: All move analyses
            color: "white" or "black"
            username: Player username
            rating: Player rating
            critical_moments: Critical moments in game

        Returns:
            Player analysis
        """
        # Filter moves for this color
        color_moves = [m for m in moves_analysis if m.color == color]

        if not color_moves:
            # Return empty analysis
            return PlayerAnalysis(
                username=username,
                color=color,
                rating=rating,
                accuracy=0.0,
                avg_centipawn_loss=0.0,
            )

        # Count move classifications
        classification_counts = Counter(m.classification.value for m in color_moves)

        # Calculate accuracy
        accuracy = self.blunder_detector.calculate_accuracy(moves_analysis, color)

        # Calculate average centipawn loss
        total_loss = sum(m.eval_loss for m in color_moves if m.eval_loss)
        avg_centipawn_loss = total_loss / len(color_moves) if color_moves else 0.0

        # Extract patterns for this player
        all_patterns = []
        for move in color_moves:
            all_patterns.extend(move.tactical_patterns)

        pattern_types = list(set(p.pattern_type for p in all_patterns))

        # Analyze by game phase
        opening_phase = self._analyze_phase(color_moves, 0, 15, "opening")
        middlegame_phase = self._analyze_phase(color_moves, 15, 40, "middlegame")
        endgame_phase = self._analyze_phase(color_moves, 40, 1000, "endgame")

        # Get player's critical moments
        player_critical_moments = [
            cm for cm in critical_moments
            if color_moves and any(
                m.move_number == cm.move_number and m.color == color
                for m in color_moves
            )
        ]

        return PlayerAnalysis(
            username=username,
            color=color,
            rating=rating,
            accuracy=accuracy,
            avg_centipawn_loss=round(avg_centipawn_loss, 1),
            brilliant_moves=classification_counts.get("brilliant", 0),
            best_moves=classification_counts.get("best", 0),
            good_moves=classification_counts.get("good", 0),
            inaccuracies=classification_counts.get("inaccuracy", 0),
            mistakes=classification_counts.get("mistake", 0),
            blunders=classification_counts.get("blunder", 0) +
                     classification_counts.get("critical_blunder", 0),
            patterns_detected=pattern_types,
            opening_phase=opening_phase,
            middlegame_phase=middlegame_phase,
            endgame_phase=endgame_phase,
            time_management_score=None,  # TODO: Calculate from time data
            critical_moments=player_critical_moments,
        )

    def _analyze_phase(
        self,
        moves: List[MoveAnalysis],
        start_move: int,
        end_move: int,
        phase_name: str,
    ) -> Optional[GamePhaseStats]:
        """
        Analyze a specific game phase.

        Args:
            moves: Player's moves
            start_move: Starting move number
            end_move: Ending move number
            phase_name: Name of phase

        Returns:
            Phase statistics or None if phase didn't occur
        """
        phase_moves = [
            m for m in moves
            if start_move <= m.move_number < end_move
        ]

        if not phase_moves:
            return None

        # Count errors
        blunders = sum(
            1 for m in phase_moves
            if m.classification.value in ["blunder", "critical_blunder"]
        )
        mistakes = sum(1 for m in phase_moves if m.classification.value == "mistake")
        inaccuracies = sum(1 for m in phase_moves if m.classification.value == "inaccuracy")

        # Calculate accuracy for phase
        good_moves = sum(
            1 for m in phase_moves
            if m.classification.value in ["brilliant", "best", "good"]
        )
        accuracy = (good_moves / len(phase_moves)) * 100 if phase_moves else 0.0

        # Average centipawn loss
        total_loss = sum(m.eval_loss for m in phase_moves if m.eval_loss)
        avg_loss = total_loss / len(phase_moves) if phase_moves else 0.0

        return GamePhaseStats(
            phase=phase_name,
            move_count=len(phase_moves),
            accuracy=round(accuracy, 1),
            blunders=blunders,
            mistakes=mistakes,
            inaccuracies=inaccuracies,
            avg_centipawn_loss=round(avg_loss, 1),
        )

    def _get_board_at_position(
        self,
        game: chess.pgn.Game,
        move_number: int
    ) -> Optional[chess.Board]:
        """
        Get board position at specific move.

        Args:
            game: PGN game
            move_number: Move number (1-indexed)

        Returns:
            Board at that position or None
        """
        board = game.board()
        node = game
        count = 0

        while node.variations and count < move_number:
            node = node.variation(0)
            board.push(node.move)
            count += 1

        return board if count == move_number else None

    def _parse_rating(self, rating_str: Optional[str]) -> Optional[int]:
        """Parse rating from PGN header."""
        if not rating_str or rating_str == "?":
            return None
        try:
            return int(rating_str)
        except ValueError:
            return None

    def _parse_time_from_comment(self, comment: str) -> tuple[Optional[float], Optional[float]]:
        """
        Parse time spent and remaining from move comment.

        Args:
            comment: Move comment from PGN

        Returns:
            Tuple of (time_spent, time_remaining) or (None, None)
        """
        # Chess.com format: [%clk 0:05:23]
        # Time spent: [%emt 0:00:05]

        import re

        time_spent = None
        time_remaining = None

        # Parse clock time
        clk_match = re.search(r'\[%clk (\d+):(\d+):(\d+)\]', comment)
        if clk_match:
            hours, minutes, seconds = map(int, clk_match.groups())
            time_remaining = hours * 3600 + minutes * 60 + seconds

        # Parse elapsed time
        emt_match = re.search(r'\[%emt (\d+):(\d+):(\d+)\]', comment)
        if emt_match:
            hours, minutes, seconds = map(int, emt_match.groups())
            time_spent = hours * 3600 + minutes * 60 + seconds

        return time_spent, time_remaining

    def _generate_game_id(self, pgn_text: str) -> str:
        """
        Generate unique game ID from PGN.

        Args:
            pgn_text: PGN string

        Returns:
            Game ID (hash of PGN)
        """
        import hashlib
        return hashlib.sha256(pgn_text.encode()).hexdigest()[:16]
