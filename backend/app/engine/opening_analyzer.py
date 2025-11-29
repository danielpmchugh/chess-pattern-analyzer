"""
Opening analysis and ECO classification.

Analyzes the opening phase of chess games, identifies openings by ECO code,
and detects early mistakes and deviations from theory.
"""

import chess
import chess.pgn
from typing import Dict, List, Optional
from app.models.chess_models import OpeningInfo, MoveAnalysis


class OpeningAnalyzer:
    """
    Analyze opening phase and classify by ECO code.

    Provides:
    - ECO opening identification
    - Opening mistake detection
    - Theory deviation tracking
    - Opening phase statistics
    """

    # Simplified ECO database for MVP
    # In production, this would load from a comprehensive ECO database file
    ECO_DATABASE = {
        # King's Pawn (e4)
        "e2e4": {"eco": "B00", "name": "King's Pawn Opening"},
        "e2e4 e7e5": {"eco": "C20", "name": "King's Pawn Game"},
        "e2e4 e7e5 g1f3": {"eco": "C40", "name": "King's Knight Opening"},
        "e2e4 e7e5 g1f3 b8c6": {"eco": "C44", "name": "King's Pawn Game"},
        "e2e4 e7e5 g1f3 b8c6 f1b5": {"eco": "C60", "name": "Ruy Lopez"},
        "e2e4 e7e5 g1f3 b8c6 f1c4": {"eco": "C50", "name": "Italian Game"},
        "e2e4 e7e5 f1c4": {"eco": "C23", "name": "Bishop's Opening"},
        "e2e4 e7e5 b1c3": {"eco": "C25", "name": "Vienna Game"},

        # Sicilian Defense
        "e2e4 c7c5": {"eco": "B20", "name": "Sicilian Defense"},
        "e2e4 c7c5 g1f3": {"eco": "B20", "name": "Sicilian Defense"},
        "e2e4 c7c5 g1f3 d7d6": {"eco": "B50", "name": "Sicilian Defense"},
        "e2e4 c7c5 g1f3 b8c6": {"eco": "B30", "name": "Sicilian Defense, Old Sicilian"},
        "e2e4 c7c5 g1f3 e7e6": {"eco": "B40", "name": "Sicilian Defense, French Variation"},

        # French Defense
        "e2e4 e7e6": {"eco": "C00", "name": "French Defense"},
        "e2e4 e7e6 d2d4": {"eco": "C00", "name": "French Defense"},
        "e2e4 e7e6 d2d4 d7d5": {"eco": "C10", "name": "French Defense"},

        # Caro-Kann
        "e2e4 c7c6": {"eco": "B10", "name": "Caro-Kann Defense"},
        "e2e4 c7c6 d2d4": {"eco": "B10", "name": "Caro-Kann Defense"},

        # Pirc/Modern
        "e2e4 d7d6": {"eco": "B07", "name": "Pirc Defense"},
        "e2e4 g7g6": {"eco": "B06", "name": "Modern Defense"},

        # Scandinavian
        "e2e4 d7d5": {"eco": "B01", "name": "Scandinavian Defense"},

        # Alekhine
        "e2e4 g8f6": {"eco": "B02", "name": "Alekhine Defense"},

        # Queen's Pawn (d4)
        "d2d4": {"eco": "A40", "name": "Queen's Pawn Opening"},
        "d2d4 d7d5": {"eco": "D00", "name": "Queen's Pawn Game"},
        "d2d4 d7d5 c2c4": {"eco": "D06", "name": "Queen's Gambit"},
        "d2d4 d7d5 c2c4 e7e6": {"eco": "D30", "name": "Queen's Gambit Declined"},
        "d2d4 d7d5 c2c4 c7c6": {"eco": "D10", "name": "Slav Defense"},
        "d2d4 d7d5 c2c4 d5c4": {"eco": "D20", "name": "Queen's Gambit Accepted"},

        # Indian Defenses
        "d2d4 g8f6": {"eco": "A45", "name": "Indian Defense"},
        "d2d4 g8f6 c2c4": {"eco": "E00", "name": "Indian Defense"},
        "d2d4 g8f6 c2c4 e7e6": {"eco": "E00", "name": "Indian Defense"},
        "d2d4 g8f6 c2c4 g7g6": {"eco": "E60", "name": "King's Indian Defense"},
        "d2d4 g8f6 c2c4 e7e6 b1c3 f8b4": {"eco": "E40", "name": "Nimzo-Indian Defense"},

        # English Opening
        "c2c4": {"eco": "A10", "name": "English Opening"},
        "c2c4 e7e5": {"eco": "A20", "name": "English Opening"},
        "c2c4 g8f6": {"eco": "A10", "name": "English Opening"},

        # Reti Opening
        "g1f3": {"eco": "A04", "name": "Reti Opening"},
        "g1f3 d7d5": {"eco": "A06", "name": "Reti Opening"},
        "g1f3 g8f6": {"eco": "A09", "name": "Reti Opening"},

        # Other
        "b2b3": {"eco": "A01", "name": "Nimzowitsch-Larsen Attack"},
        "f2f4": {"eco": "A02", "name": "Bird's Opening"},
    }

    def __init__(self):
        """Initialize opening analyzer."""
        self.opening_phase_moves = 15  # Analyze first 15 moves as opening

    async def analyze_opening(
        self,
        moves_uci: List[str],
        move_analyses: List[MoveAnalysis],
    ) -> OpeningInfo:
        """
        Analyze opening phase of the game.

        Args:
            moves_uci: List of moves in UCI notation
            move_analyses: Complete move analyses (including evaluations)

        Returns:
            OpeningInfo with classification and mistakes
        """
        # Identify the opening
        eco, name = self._identify_opening(moves_uci)

        # Extract opening phase moves (first 15 or until opening phase ends)
        opening_moves_uci = moves_uci[:self.opening_phase_moves]

        # Convert UCI to SAN for display (simplified - would need board state)
        opening_moves_san = opening_moves_uci  # TODO: Convert to SAN properly

        # Find opening mistakes (significant errors in first 15 moves)
        opening_mistakes = []
        deviation_move = None

        for i, move_analysis in enumerate(move_analyses[:self.opening_phase_moves]):
            # Check for mistakes/blunders in opening
            if move_analysis.classification.value in ["mistake", "blunder", "critical_blunder"]:
                opening_mistakes.append(move_analysis)

            # Track deviation from theory (first significant inaccuracy)
            if deviation_move is None and move_analysis.eval_loss > 50:
                deviation_move = move_analysis.move_number

        # Calculate opening accuracy
        if move_analyses:
            opening_phase_analyses = move_analyses[:self.opening_phase_moves]
            good_moves = sum(
                1 for m in opening_phase_analyses
                if m.classification.value in ["brilliant", "best", "good", "book"]
            )
            opening_accuracy = (good_moves / len(opening_phase_analyses)) * 100 if opening_phase_analyses else 0.0
        else:
            opening_accuracy = 0.0

        return OpeningInfo(
            eco=eco,
            name=name,
            moves=opening_moves_san,
            moves_uci=opening_moves_uci,
            deviation_move=deviation_move,
            mistakes_in_opening=opening_mistakes,
            opening_accuracy=opening_accuracy,
        )

    def _identify_opening(self, moves_uci: List[str]) -> tuple[str, str]:
        """
        Identify opening from move sequence.

        Args:
            moves_uci: List of moves in UCI notation

        Returns:
            Tuple of (ECO code, opening name)
        """
        if not moves_uci:
            return "A00", "Unknown Opening"

        # Try progressively longer sequences (from longest to shortest)
        # This ensures we get the most specific classification
        for length in range(min(len(moves_uci), 8), 0, -1):
            sequence = " ".join(moves_uci[:length])

            if sequence in self.ECO_DATABASE:
                opening = self.ECO_DATABASE[sequence]
                return opening["eco"], opening["name"]

        # If no match found, classify by first move
        first_move = moves_uci[0]

        # Basic first move classification
        if first_move == "e2e4":
            return "B00", "King's Pawn Opening"
        elif first_move == "d2d4":
            return "A40", "Queen's Pawn Opening"
        elif first_move == "c2c4":
            return "A10", "English Opening"
        elif first_move == "g1f3":
            return "A04", "Reti Opening"
        else:
            return "A00", "Uncommon Opening"

    def get_opening_principles_score(self, board: chess.Board, move_number: int) -> float:
        """
        Score how well opening principles are being followed.

        Principles:
        - Control center
        - Develop pieces
        - Castle early
        - Don't move same piece twice
        - Don't bring queen out too early

        Args:
            board: Current position
            move_number: Current move number

        Returns:
            Score from 0-100
        """
        if move_number > 15:
            return 100.0  # Not in opening anymore

        score = 100.0
        color = board.turn

        # Check piece development
        developed_pieces = 0
        total_minor_pieces = 4  # 2 knights, 2 bishops

        for piece_type in [chess.KNIGHT, chess.BISHOP]:
            for square in board.pieces(piece_type, color):
                rank = chess.square_rank(square)
                # Check if piece has moved from starting position
                starting_rank = 0 if color == chess.WHITE else 7
                if rank != starting_rank:
                    developed_pieces += 1

        development_score = (developed_pieces / total_minor_pieces) * 30
        score = development_score

        # Check center control
        center_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
        center_control = sum(
            1 for sq in center_squares
            if board.is_attacked_by(color, sq)
        )
        score += (center_control / 4) * 25

        # Check if castled
        if board.has_castling_rights(color):
            if move_number > 10:
                score -= 15  # Penalty for not castling by move 10
        else:
            # Has castled (lost castling rights by castling)
            # Actually need to check if castled vs lost rights
            score += 20

        # Check for premature queen moves
        queen_square = board.king(color)  # Placeholder
        # This would require tracking if queen moved early
        # Simplified for MVP

        # Check pawn structure
        # Penalty for weakened king safety

        return min(100.0, max(0.0, score))

    def get_common_opening_mistakes(self) -> List[Dict]:
        """
        Get list of common opening mistakes to watch for.

        Returns:
            List of common mistake patterns with descriptions
        """
        return [
            {
                "mistake": "moving_same_piece_twice",
                "description": "Moving the same piece multiple times in the opening",
                "severity": "medium",
            },
            {
                "mistake": "early_queen_development",
                "description": "Developing queen too early (before move 5)",
                "severity": "medium",
            },
            {
                "mistake": "neglecting_center_control",
                "description": "Not fighting for central squares (d4, e4, d5, e5)",
                "severity": "high",
            },
            {
                "mistake": "delaying_castling",
                "description": "Not castling before move 12-15",
                "severity": "medium",
            },
            {
                "mistake": "ignoring_development",
                "description": "Moving pawns instead of developing pieces",
                "severity": "high",
            },
            {
                "mistake": "creating_pawn_weaknesses",
                "description": "Creating holes or weak squares in pawn structure",
                "severity": "medium",
            },
            {
                "mistake": "blocking_own_pieces",
                "description": "Blocking development of own pieces",
                "severity": "medium",
            },
        ]

    def add_opening_to_database(self, moves_uci: List[str], eco: str, name: str) -> None:
        """
        Add a new opening to the database.

        Args:
            moves_uci: Opening move sequence in UCI
            eco: ECO code
            name: Opening name
        """
        key = " ".join(moves_uci)
        self.ECO_DATABASE[key] = {"eco": eco, "name": name}

    def get_database_size(self) -> int:
        """Get number of openings in database."""
        return len(self.ECO_DATABASE)
