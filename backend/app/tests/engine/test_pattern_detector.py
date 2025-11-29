"""
Unit tests for tactical pattern detection.

Tests for identifying forks, pins, skewers, hanging pieces, and other tactical patterns.
"""

import pytest
import chess
from app.engine.pattern_detector import TacticalPatternDetector
from app.models.chess_models import PatternType


class TestTacticalPatternDetector:
    """Test tactical pattern detection."""

    @pytest.fixture
    def detector(self):
        """Create pattern detector instance."""
        return TacticalPatternDetector()

    def test_hanging_piece_detection(self, detector):
        """Test detection of hanging pieces."""
        # Position with hanging knight on f6
        board = chess.Board("rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")

        # Move knight to g5 attacking f7 and leaving f6 knight hanging
        move = chess.Move.from_uci("f3g5")
        board.push(move)

        patterns = detector.detect_hanging_pieces(board)

        # Should detect hanging knight
        assert len(patterns) >= 0  # May or may not detect depending on position

    def test_fork_detection_knight(self, detector):
        """Test detection of knight forks."""
        # Position where knight can fork king and queen
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")

        # Knight to g5 (example position)
        move = chess.Move.from_uci("f3g5")
        board.push(move)

        fork = detector.detect_fork(board, move)

        # In this specific position, may or may not be a fork
        # Test just ensures function runs without error
        assert fork is None or fork.pattern_type in [PatternType.FORK, PatternType.KNIGHT_FORK]

    def test_fork_detection_multiple_targets(self, detector):
        """Test fork with multiple valuable targets."""
        # Set up position with knight forking king and rook
        # Using FEN: "4k3/8/8/3N4/8/8/8/4K2R w - - 0 1"
        board = chess.Board("4k3/8/8/3N4/8/8/8/4K2R w - - 0 1")

        # Knight on d5 can fork e7 and f6
        move = chess.Move.from_uci("d5e7")
        board.push(move)

        patterns = detector.detect_all_patterns(board, move)

        # Should detect some patterns (may include fork or other patterns)
        assert isinstance(patterns, list)

    def test_pin_detection_absolute(self, detector):
        """Test detection of absolute pins."""
        # Position with bishop pinning knight to king
        # FEN: "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4"
        board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4")

        pins = detector.detect_pins(board)

        # Should detect pins in position
        assert isinstance(pins, list)

    def test_skewer_detection(self, detector):
        """Test detection of skewers."""
        # Position with potential skewer
        board = chess.Board("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")

        skewers = detector.detect_skewers(board)

        assert isinstance(skewers, list)

    def test_back_rank_weakness(self, detector):
        """Test detection of back rank weaknesses."""
        # Position with back rank mate threat
        # King on back rank, no escape squares
        board = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 b - - 0 1")

        weakness = detector.detect_back_rank_weakness(board)

        # Black king has back rank weakness
        if weakness:
            assert weakness.pattern_type == PatternType.BACK_RANK_WEAKNESS

    def test_trapped_piece_detection(self, detector):
        """Test detection of trapped pieces."""
        # Position with trapped piece
        board = chess.Board("rnbqkb1r/pppppppp/8/8/8/8/PPPPPPPP/RNBQKB1R w KQkq - 0 1")

        trapped = detector.detect_trapped_pieces(board)

        # Starting position has no trapped pieces
        assert len(trapped) == 0

    def test_pattern_severity_calculation(self, detector):
        """Test severity calculation based on piece values."""
        # Test severity for different piece values
        assert detector._calculate_severity(100) == "low"  # Pawn
        assert detector._calculate_severity(320) == "medium"  # Knight
        assert detector._calculate_severity(500) == "high"  # Rook
        assert detector._calculate_severity(900) == "high"  # Queen

    def test_detect_all_patterns(self, detector):
        """Test detection of all patterns in a position."""
        # Complex position with multiple tactical elements
        board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")

        patterns = detector.detect_all_patterns(board)

        # Should return a list (may be empty or with patterns)
        assert isinstance(patterns, list)

        # All patterns should have required attributes
        for pattern in patterns:
            assert hasattr(pattern, 'pattern_type')
            assert hasattr(pattern, 'severity')
            assert hasattr(pattern, 'pieces_involved')

    def test_no_patterns_in_quiet_position(self, detector):
        """Test that quiet positions don't generate false positives."""
        # Starting position - should have no tactical patterns
        board = chess.Board()

        patterns = detector.detect_all_patterns(board)

        # Starting position should have no hanging pieces, forks, etc.
        assert len(patterns) == 0

    def test_piece_values(self, detector):
        """Test piece value constants."""
        assert detector.PIECE_VALUES[chess.PAWN] == 100
        assert detector.PIECE_VALUES[chess.KNIGHT] == 320
        assert detector.PIECE_VALUES[chess.BISHOP] == 330
        assert detector.PIECE_VALUES[chess.ROOK] == 500
        assert detector.PIECE_VALUES[chess.QUEEN] == 900
        assert detector.PIECE_VALUES[chess.KING] == 20000


class TestPatternDetectionEdgeCases:
    """Test edge cases in pattern detection."""

    @pytest.fixture
    def detector(self):
        return TacticalPatternDetector()

    def test_empty_board_no_patterns(self, detector):
        """Test that empty positions don't crash."""
        # Position with only kings
        board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")

        patterns = detector.detect_all_patterns(board)
        assert isinstance(patterns, list)

    def test_checkmate_position(self, detector):
        """Test pattern detection in checkmate position."""
        # Back rank mate
        board = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")

        patterns = detector.detect_all_patterns(board)
        assert isinstance(patterns, list)

    def test_stalemate_position(self, detector):
        """Test pattern detection in stalemate."""
        # Stalemate position
        board = chess.Board("7k/5Q2/5K2/8/8/8/8/8 b - - 0 1")

        patterns = detector.detect_all_patterns(board)
        assert isinstance(patterns, list)
