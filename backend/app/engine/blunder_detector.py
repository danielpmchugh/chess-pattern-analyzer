"""
Blunder detection and move classification.

Classifies moves as brilliant, good, inaccuracy, mistake, or blunder based on
engine evaluation. Identifies specific types of blunders.
"""

import chess
from typing import Optional, Dict, List
from app.models.chess_models import (
    MoveClassification,
    BlunderType,
    MoveAnalysis,
    AlternativeMove,
    PositionEvaluation,
)
from app.engine.stockfish_manager import StockfishManager


class BlunderDetector:
    """
    Detect and classify blunders and mistakes in chess games.

    Classifies moves based on centipawn loss:
    - Brilliant: Sacrifice that leads to advantage
    - Best: Engine's top move
    - Good: < 50cp loss (< 0.5 pawns)
    - Inaccuracy: 50-100cp loss (0.5-1 pawn)
    - Mistake: 100-200cp loss (1-2 pawns)
    - Blunder: 200-400cp loss (2-4 pawns)
    - Critical Blunder: > 400cp loss (> 4 pawns)
    """

    # Classification thresholds in centipawns
    THRESHOLDS = {
        "inaccuracy": 50,
        "mistake": 100,
        "blunder": 200,
        "critical_blunder": 400,
    }

    # Mate score (treat mates as extreme eval)
    MATE_SCORE = 10000

    def __init__(self):
        """Initialize blunder detector."""
        pass

    async def analyze_move(
        self,
        board_before: chess.Board,
        move: chess.Move,
        engine: StockfishManager,
        move_number: int,
        half_move: int,
        time_spent: Optional[float] = None,
        time_remaining: Optional[float] = None,
    ) -> MoveAnalysis:
        """
        Analyze a single move and classify it.

        Args:
            board_before: Position before the move
            move: The move played
            engine: Stockfish engine manager
            move_number: Full move number (1, 2, 3...)
            half_move: Half-move ply count
            time_spent: Time spent on this move (optional)
            time_remaining: Time remaining after move (optional)

        Returns:
            Complete move analysis
        """
        color = "white" if board_before.turn == chess.WHITE else "black"

        # Get evaluation before move and best alternatives
        analysis_before = await engine.analyze_position(board_before)
        top_moves = await engine.get_top_moves(board_before, num_moves=3)

        eval_before = self._extract_centipawns(analysis_before)
        best_move_uci = top_moves[0]["move"] if top_moves else None
        best_eval = self._extract_centipawns_from_move(top_moves[0]) if top_moves else eval_before

        # Make the move
        board_after = board_before.copy()
        san_notation = board_before.san(move)
        board_after.push(move)

        # Get evaluation after move
        analysis_after = await engine.analyze_position(board_after)
        eval_after = self._extract_centipawns(analysis_after)

        # Calculate evaluation loss (from perspective of player who moved)
        # Need to negate eval_after since it's from opponent's perspective after the move
        eval_loss = self._calculate_eval_loss(
            eval_before,
            -eval_after,  # Negate because turn changed
            best_eval,
            board_before.turn
        )

        # Classify the move
        classification = self._classify_move(
            move.uci(),
            best_move_uci,
            eval_loss,
            eval_before,
            -eval_after
        )

        # Determine blunder type if applicable
        blunder_type = None
        if classification.value in ["mistake", "blunder", "critical_blunder"]:
            blunder_type = await self._identify_blunder_type(
                board_before,
                move,
                board_after,
                eval_loss
            )

        # Build alternative moves
        alternatives = []
        for i, alt_move in enumerate(top_moves[:3]):
            if alt_move["move"]:
                # Create a board to get SAN
                test_board = board_before.copy()
                alt_move_obj = chess.Move.from_uci(alt_move["move"])
                alt_san = test_board.san(alt_move_obj)

                alternatives.append(AlternativeMove(
                    move=alt_move["move"],
                    san=alt_san,
                    evaluation=PositionEvaluation(
                        centipawns=alt_move.get("score"),
                        mate_in=alt_move.get("mate"),
                        depth=analysis_before.get("depth", 18),
                        best_move=None,
                    ),
                    description=f"Alternative #{i+1}" if i > 0 else "Best move"
                ))

        # Get best move in SAN
        best_move_san = None
        if best_move_uci:
            test_board = board_before.copy()
            best_move_san = test_board.san(chess.Move.from_uci(best_move_uci))

        return MoveAnalysis(
            move_number=move_number,
            half_move=half_move,
            color=color,
            move=move.uci(),
            san=san_notation,
            classification=classification,
            eval_before=eval_before,
            eval_after=-eval_after,  # Store from same perspective
            best_move=best_move_uci,
            best_move_san=best_move_san,
            best_eval=best_eval,
            eval_loss=abs(eval_loss),
            blunder_type=blunder_type,
            tactical_patterns=[],  # Will be filled by pattern detector
            alternatives=alternatives,
            time_spent=time_spent,
            time_remaining=time_remaining,
            position_fen=board_after.fen(),
        )

    def _extract_centipawns(self, analysis: Dict) -> Optional[int]:
        """
        Extract centipawn evaluation from analysis.

        Args:
            analysis: Stockfish analysis result

        Returns:
            Centipawn evaluation or None
        """
        if analysis.get("mate") is not None:
            mate_in = analysis["mate"]
            # Return high score for mate, sign indicates who is mating
            return self.MATE_SCORE if mate_in > 0 else -self.MATE_SCORE

        return analysis.get("score")

    def _extract_centipawns_from_move(self, move_info: Dict) -> Optional[int]:
        """Extract centipawns from top move info."""
        if move_info.get("mate") is not None:
            mate_in = move_info["mate"]
            return self.MATE_SCORE if mate_in > 0 else -self.MATE_SCORE
        return move_info.get("score")

    def _calculate_eval_loss(
        self,
        eval_before: Optional[int],
        eval_after: Optional[int],
        best_eval: Optional[int],
        turn: chess.Color,
    ) -> int:
        """
        Calculate centipawn loss from the move.

        Args:
            eval_before: Evaluation before move
            eval_after: Evaluation after move (already negated)
            best_eval: Best move evaluation
            turn: Color to move

        Returns:
            Centipawn loss (positive value)
        """
        # Handle None cases
        if eval_before is None or eval_after is None or best_eval is None:
            return 0

        # Evaluation loss is difference between best move and actual move
        # From the perspective of the player who moved
        loss = best_eval - eval_after

        return int(loss)

    def _classify_move(
        self,
        move_uci: str,
        best_move_uci: Optional[str],
        eval_loss: int,
        eval_before: Optional[int],
        eval_after: Optional[int],
    ) -> MoveClassification:
        """
        Classify move quality based on evaluation loss.

        Args:
            move_uci: Move played (UCI)
            best_move_uci: Best move (UCI)
            eval_loss: Centipawn loss
            eval_before: Eval before move
            eval_after: Eval after move

        Returns:
            Move classification
        """
        # Check if it's the best move
        if move_uci == best_move_uci:
            # Check if it's a brilliant sacrifice
            if self._is_brilliant_sacrifice(eval_before, eval_after, eval_loss):
                return MoveClassification.BRILLIANT
            return MoveClassification.BEST

        # Classify based on centipawn loss
        abs_loss = abs(eval_loss)

        if abs_loss < self.THRESHOLDS["inaccuracy"]:
            return MoveClassification.GOOD
        elif abs_loss < self.THRESHOLDS["mistake"]:
            return MoveClassification.INACCURACY
        elif abs_loss < self.THRESHOLDS["blunder"]:
            return MoveClassification.MISTAKE
        elif abs_loss < self.THRESHOLDS["critical_blunder"]:
            return MoveClassification.BLUNDER
        else:
            return MoveClassification.CRITICAL_BLUNDER

    def _is_brilliant_sacrifice(
        self,
        eval_before: Optional[int],
        eval_after: Optional[int],
        eval_loss: int,
    ) -> bool:
        """
        Determine if move is a brilliant sacrifice.

        A brilliant move:
        - Sacrifices material (eval appears to drop)
        - But leads to winning advantage
        - Is not obvious (requires deep calculation)

        Args:
            eval_before: Eval before move
            eval_after: Eval after move
            eval_loss: Centipawn loss

        Returns:
            True if move is brilliant
        """
        # For MVP, using simple heuristic:
        # Brilliant if move looks bad initially but leads to winning position

        if eval_before is None or eval_after is None:
            return False

        # Move appears to sacrifice (loses material in shallow analysis)
        # But deep analysis shows it's actually winning
        # This requires comparing shallow vs deep analysis
        # For MVP, we'll mark very few moves as brilliant

        # Only mark as brilliant if:
        # 1. Final eval is significantly winning (> +300cp)
        # 2. Move involves some complexity (sacrifices or tactics)

        if eval_after > 300 and abs(eval_loss) < 50:
            # Strong winning position after the move, very small loss
            # Could indicate a deep tactical move
            return False  # Conservative for MVP

        return False

    async def _identify_blunder_type(
        self,
        board_before: chess.Board,
        move: chess.Move,
        board_after: chess.Board,
        eval_loss: int,
    ) -> BlunderType:
        """
        Identify the specific type of blunder.

        Args:
            board_before: Position before move
            move: Move played
            board_after: Position after move
            eval_loss: Centipawn loss

        Returns:
            Specific blunder type
        """
        # Check for hanging piece
        if self._leaves_piece_hanging(board_after, move):
            return BlunderType.HANGING_PIECE

        # Check for missed checkmate
        if self._missed_checkmate(board_before):
            return BlunderType.MISSED_CHECKMATE

        # Check if move allows immediate tactics
        if self._allows_immediate_tactic(board_after, eval_loss):
            return BlunderType.ALLOWS_TACTIC

        # Check for opening mistakes (first 15 moves)
        move_number = board_after.fullmove_number
        if move_number <= 15:
            return BlunderType.OPENING_MISTAKE

        # Check for endgame mistakes
        if self._is_endgame(board_after) and eval_loss > 200:
            return BlunderType.ENDGAME_TECHNIQUE

        # Check for positional blunder
        if self._is_positional_blunder(board_before, move, eval_loss):
            return BlunderType.POSITIONAL_BLUNDER

        return BlunderType.UNSPECIFIED

    def _leaves_piece_hanging(self, board: chess.Board, last_move: chess.Move) -> bool:
        """
        Check if the move left a piece hanging.

        Args:
            board: Position after move
            last_move: Move that was played

        Returns:
            True if move left piece hanging
        """
        # Check if the piece that moved is now hanging
        moved_piece = board.piece_at(last_move.to_square)
        if not moved_piece:
            return False

        # Check if piece is attacked and undefended
        attackers = board.attackers(not moved_piece.color, last_move.to_square)
        defenders = board.attackers(moved_piece.color, last_move.to_square)

        return len(attackers) > 0 and len(defenders) == 0

    def _missed_checkmate(self, board: chess.Board) -> bool:
        """
        Check if player missed a checkmate.

        Args:
            board: Position before move

        Returns:
            True if checkmate was available
        """
        # Check all legal moves for checkmate
        for move in board.legal_moves:
            board_copy = board.copy()
            board_copy.push(move)
            if board_copy.is_checkmate():
                return True

        return False

    def _allows_immediate_tactic(self, board: chess.Board, eval_loss: int) -> bool:
        """
        Check if move allows opponent an immediate tactic.

        Args:
            board: Position after move
            eval_loss: Centipawn loss

        Returns:
            True if move allows tactics
        """
        # Large eval loss indicates opponent now has strong tactic
        # Also check if opponent has forcing moves (checks, captures)

        if eval_loss < 150:
            return False

        # Check if opponent has checks or captures
        has_tactics = False
        for move in board.legal_moves:
            if board.is_capture(move) or board.gives_check(move):
                has_tactics = True
                break

        return has_tactics

    def _is_endgame(self, board: chess.Board) -> bool:
        """
        Determine if position is in endgame phase.

        Simple heuristic: endgame if queens are off or few pieces remain.

        Args:
            board: Chess position

        Returns:
            True if in endgame
        """
        # Count queens
        white_queens = len(board.pieces(chess.QUEEN, chess.WHITE))
        black_queens = len(board.pieces(chess.QUEEN, chess.BLACK))

        # No queens = endgame
        if white_queens == 0 and black_queens == 0:
            return True

        # Count total pieces (excluding kings and pawns)
        total_pieces = 0
        for piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]:
            total_pieces += len(board.pieces(piece_type, chess.WHITE))
            total_pieces += len(board.pieces(piece_type, chess.BLACK))

        # Few pieces = endgame
        return total_pieces <= 6

    def _is_positional_blunder(
        self,
        board_before: chess.Board,
        move: chess.Move,
        eval_loss: int,
    ) -> bool:
        """
        Check if blunder is positional in nature.

        Positional blunders:
        - Weakening pawn structure
        - Placing pieces on bad squares
        - Giving up important squares
        - Trading good pieces for bad

        Args:
            board_before: Position before move
            move: Move played
            eval_loss: Centipawn loss

        Returns:
            True if positional blunder
        """
        # Moderate eval loss without immediate tactics suggests positional error
        if 100 <= eval_loss <= 250:
            # Check if move weakened pawn structure or piece positioning
            # For MVP, this is a simplified check
            return not board_before.is_capture(move) and not board_before.gives_check(move)

        return False

    def calculate_accuracy(self, move_analyses: List[MoveAnalysis], color: str) -> float:
        """
        Calculate accuracy percentage for a player.

        Uses weighted formula based on move quality.

        Args:
            move_analyses: List of all move analyses
            color: "white" or "black"

        Returns:
            Accuracy from 0-100
        """
        # Filter moves for this color
        color_moves = [
            m for m in move_analyses
            if m.color == color
        ]

        if not color_moves:
            return 0.0

        # Calculate accuracy based on classification distribution
        weights = {
            MoveClassification.BRILLIANT: 1.0,
            MoveClassification.BEST: 1.0,
            MoveClassification.GOOD: 0.95,
            MoveClassification.BOOK: 1.0,
            MoveClassification.INACCURACY: 0.80,
            MoveClassification.MISTAKE: 0.60,
            MoveClassification.BLUNDER: 0.30,
            MoveClassification.CRITICAL_BLUNDER: 0.0,
        }

        total_weight = sum(weights.get(m.classification, 0.5) for m in color_moves)
        accuracy = (total_weight / len(color_moves)) * 100

        return round(accuracy, 1)
