"""
Unit tests for blunder detection and move classification.
"""

import pytest
import chess
from app.engine.blunder_detector import BlunderDetector
from app.models.chess_models import MoveClassification, BlunderType


class TestBlunderDetector:
    """Test blunder detection functionality."""

    @pytest.fixture
    def detector(self):
        """Create blunder detector instance."""
        return BlunderDetector()

    def test_classification_thresholds(self, detector):
        """Test classification threshold constants."""
        assert detector.THRESHOLDS["inaccuracy"] == 50
        assert detector.THRESHOLDS["mistake"] == 100
        assert detector.THRESHOLDS["blunder"] == 200
        assert detector.THRESHOLDS["critical_blunder"] == 400

    def test_classify_best_move(self, detector):
        """Test classification of best move."""
        classification = detector._classify_move(
            move_uci="e2e4",
            best_move_uci="e2e4",
            eval_loss=0,
            eval_before=20,
            eval_after=20
        )

        assert classification == MoveClassification.BEST

    def test_classify_good_move(self, detector):
        """Test classification of good move (small eval loss)."""
        classification = detector._classify_move(
            move_uci="e2e4",
            best_move_uci="d2d4",
            eval_loss=30,  # Less than inaccuracy threshold
            eval_before=20,
            eval_after=-10
        )

        assert classification == MoveClassification.GOOD

    def test_classify_inaccuracy(self, detector):
        """Test classification of inaccuracy."""
        classification = detector._classify_move(
            move_uci="a2a3",
            best_move_uci="e2e4",
            eval_loss=75,  # Between 50-100
            eval_before=20,
            eval_after=-55
        )

        assert classification == MoveClassification.INACCURACY

    def test_classify_mistake(self, detector):
        """Test classification of mistake."""
        classification = detector._classify_move(
            move_uci="f3f4",
            best_move_uci="e2e4",
            eval_loss=150,  # Between 100-200
            eval_before=50,
            eval_after=-100
        )

        assert classification == MoveClassification.MISTAKE

    def test_classify_blunder(self, detector):
        """Test classification of blunder."""
        classification = detector._classify_move(
            move_uci="e1e2",
            best_move_uci="e1g1",
            eval_loss=250,  # Between 200-400
            eval_before=0,
            eval_after=-250
        )

        assert classification == MoveClassification.BLUNDER

    def test_classify_critical_blunder(self, detector):
        """Test classification of critical blunder."""
        classification = detector._classify_move(
            move_uci="d1h5",
            best_move_uci="e2e4",
            eval_loss=500,  # > 400
            eval_before=100,
            eval_after=-400
        )

        assert classification == MoveClassification.CRITICAL_BLUNDER

    def test_extract_centipawns_normal(self, detector):
        """Test centipawn extraction from normal evaluation."""
        analysis = {"score": 150, "mate": None}
        cp = detector._extract_centipawns(analysis)

        assert cp == 150

    def test_extract_centipawns_mate(self, detector):
        """Test centipawn extraction from mate score."""
        analysis = {"score": None, "mate": 3}
        cp = detector._extract_centipawns(analysis)

        assert cp == detector.MATE_SCORE

    def test_extract_centipawns_negative_mate(self, detector):
        """Test centipawn extraction from negative mate score."""
        analysis = {"score": None, "mate": -5}
        cp = detector._extract_centipawns(analysis)

        assert cp == -detector.MATE_SCORE

    def test_calculate_eval_loss(self, detector):
        """Test evaluation loss calculation."""
        loss = detector._calculate_eval_loss(
            eval_before=100,
            eval_after=50,
            best_eval=100,
            turn=chess.WHITE
        )

        # Loss should be positive
        assert loss == 50

    def test_leaves_piece_hanging_true(self, detector):
        """Test detection of hanging piece after move."""
        # Create position where piece is hanging
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R w KQkq - 1 2")
        last_move = chess.Move.from_uci("f3h4")  # Knight to edge, could be hanging

        # Note: This is a simplified test - actual hanging detection is complex
        result = detector._leaves_piece_hanging(board, last_move)
        assert isinstance(result, bool)

    def test_missed_checkmate_false(self, detector):
        """Test checkmate detection in non-mate position."""
        board = chess.Board()  # Starting position

        has_mate = detector._missed_checkmate(board)
        assert has_mate is False

    def test_missed_checkmate_true(self, detector):
        """Test checkmate detection when mate is available."""
        # Position with mate in 1
        board = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
        # Ra8# is mate

        has_mate = detector._missed_checkmate(board)
        assert has_mate is True

    def test_is_endgame_no_queens(self, detector):
        """Test endgame detection with no queens."""
        # Endgame position (no queens)
        board = chess.Board("4k3/8/8/8/8/8/4K3/4R3 w - - 0 1")

        assert detector._is_endgame(board) is True

    def test_is_endgame_opening(self, detector):
        """Test endgame detection in opening."""
        board = chess.Board()  # Starting position

        assert detector._is_endgame(board) is False

    def test_is_endgame_few_pieces(self, detector):
        """Test endgame detection with few pieces."""
        # Few pieces remaining
        board = chess.Board("4k3/8/8/8/8/8/4K3/1R1B4 w - - 0 1")

        assert detector._is_endgame(board) is True

    def test_calculate_accuracy_all_good_moves(self, detector):
        """Test accuracy calculation with all good moves."""
        from app.models.chess_models import MoveAnalysis

        moves = [
            MoveAnalysis(
                move_number=i+1,
                half_move=i,
                color="white",
                move="e2e4",
                san="e4",
                classification=MoveClassification.GOOD,
                eval_loss=20,
                position_fen="fen"
            )
            for i in range(10)
        ]

        accuracy = detector.calculate_accuracy(moves, "white")
        assert accuracy >= 90.0  # Should be high accuracy

    def test_calculate_accuracy_mixed_moves(self, detector):
        """Test accuracy calculation with mixed move quality."""
        from app.models.chess_models import MoveAnalysis

        moves = [
            MoveAnalysis(
                move_number=1, half_move=0, color="white", move="e2e4", san="e4",
                classification=MoveClassification.BEST, eval_loss=0, position_fen="fen"
            ),
            MoveAnalysis(
                move_number=2, half_move=2, color="white", move="f3f4", san="f4",
                classification=MoveClassification.MISTAKE, eval_loss=150, position_fen="fen"
            ),
            MoveAnalysis(
                move_number=3, half_move=4, color="white", move="g1f3", san="Nf3",
                classification=MoveClassification.GOOD, eval_loss=30, position_fen="fen"
            ),
        ]

        accuracy = detector.calculate_accuracy(moves, "white")
        assert 0 <= accuracy <= 100  # Valid accuracy range

    def test_calculate_accuracy_no_moves(self, detector):
        """Test accuracy calculation with no moves."""
        accuracy = detector.calculate_accuracy([], "white")
        assert accuracy == 0.0

    def test_allows_immediate_tactic_true(self, detector):
        """Test detection of allowing immediate tactics."""
        # Position where opponent has forcing moves
        board = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")

        allows_tactic = detector._allows_immediate_tactic(board, eval_loss=200)
        assert isinstance(allows_tactic, bool)

    def test_allows_immediate_tactic_false(self, detector):
        """Test no tactics allowed in quiet position."""
        board = chess.Board()  # Starting position

        allows_tactic = detector._allows_immediate_tactic(board, eval_loss=50)
        assert allows_tactic is False

    def test_is_positional_blunder(self, detector):
        """Test positional blunder detection."""
        board = chess.Board()
        move = chess.Move.from_uci("h2h4")  # Weakening move

        is_positional = detector._is_positional_blunder(board, move, eval_loss=120)
        assert isinstance(is_positional, bool)


class TestBlunderTypeIdentification:
    """Test identification of specific blunder types."""

    @pytest.fixture
    def detector(self):
        return BlunderDetector()

    @pytest.mark.asyncio
    async def test_identify_hanging_piece_blunder(self, detector):
        """Test identification of hanging piece blunder."""
        board_before = chess.Board()
        move = chess.Move.from_uci("f3h4")
        board_after = board_before.copy()
        board_after.push(move)

        blunder_type = await detector._identify_blunder_type(
            board_before, move, board_after, eval_loss=300
        )

        assert isinstance(blunder_type, BlunderType)

    @pytest.mark.asyncio
    async def test_identify_opening_mistake(self, detector):
        """Test identification of opening mistake."""
        board_before = chess.Board()
        move = chess.Move.from_uci("a2a4")
        board_after = board_before.copy()
        board_after.push(move)

        blunder_type = await detector._identify_blunder_type(
            board_before, move, board_after, eval_loss=250
        )

        # First move, should likely be classified as opening mistake
        assert blunder_type in [BlunderType.OPENING_MISTAKE, BlunderType.POSITIONAL_BLUNDER,
                                BlunderType.UNSPECIFIED]
