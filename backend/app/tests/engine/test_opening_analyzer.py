"""
Unit tests for opening analysis and ECO classification.
"""

import pytest
from app.engine.opening_analyzer import OpeningAnalyzer
from app.models.chess_models import MoveAnalysis, MoveClassification


class TestOpeningAnalyzer:
    """Test opening analysis functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create opening analyzer instance."""
        return OpeningAnalyzer()

    def test_identify_kings_pawn_opening(self, analyzer):
        """Test identification of King's Pawn Opening."""
        moves = ["e2e4"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "B00"
        assert "King's Pawn" in name

    def test_identify_sicilian_defense(self, analyzer):
        """Test identification of Sicilian Defense."""
        moves = ["e2e4", "c7c5"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "B20"
        assert "Sicilian" in name

    def test_identify_ruy_lopez(self, analyzer):
        """Test identification of Ruy Lopez."""
        moves = ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "C60"
        assert "Ruy Lopez" in name

    def test_identify_italian_game(self, analyzer):
        """Test identification of Italian Game."""
        moves = ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "C50"
        assert "Italian" in name

    def test_identify_queens_gambit(self, analyzer):
        """Test identification of Queen's Gambit."""
        moves = ["d2d4", "d7d5", "c2c4"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "D06"
        assert "Queen's Gambit" in name

    def test_identify_queens_gambit_declined(self, analyzer):
        """Test identification of Queen's Gambit Declined."""
        moves = ["d2d4", "d7d5", "c2c4", "e7e6"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "D30"
        assert "Declined" in name

    def test_identify_indian_defense(self, analyzer):
        """Test identification of Indian Defense."""
        moves = ["d2d4", "g8f6"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "A45"
        assert "Indian" in name

    def test_identify_kings_indian(self, analyzer):
        """Test identification of King's Indian Defense."""
        moves = ["d2d4", "g8f6", "c2c4", "g7g6"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "E60"
        assert "King's Indian" in name

    def test_identify_english_opening(self, analyzer):
        """Test identification of English Opening."""
        moves = ["c2c4"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "A10"
        assert "English" in name

    def test_identify_reti_opening(self, analyzer):
        """Test identification of Reti Opening."""
        moves = ["g1f3"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "A04"
        assert "Reti" in name

    def test_identify_french_defense(self, analyzer):
        """Test identification of French Defense."""
        moves = ["e2e4", "e7e6"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "C00"
        assert "French" in name

    def test_identify_caro_kann(self, analyzer):
        """Test identification of Caro-Kann Defense."""
        moves = ["e2e4", "c7c6"]
        eco, name = analyzer._identify_opening(moves)

        assert eco == "B10"
        assert "Caro-Kann" in name

    def test_unknown_opening(self, analyzer):
        """Test handling of unknown/uncommon openings."""
        moves = ["h2h4"]  # Uncommon first move
        eco, name = analyzer._identify_opening(moves)

        assert eco == "A00"
        assert "Uncommon" in name

    def test_empty_moves_list(self, analyzer):
        """Test handling of empty moves list."""
        moves = []
        eco, name = analyzer._identify_opening(moves)

        assert eco == "A00"
        assert "Unknown" in name

    @pytest.mark.asyncio
    async def test_analyze_opening_phase(self, analyzer):
        """Test analysis of opening phase."""
        moves_uci = ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]

        # Create dummy move analyses
        move_analyses = [
            MoveAnalysis(
                move_number=i+1,
                half_move=i,
                color="white" if i % 2 == 0 else "black",
                move=move,
                san=move,
                classification=MoveClassification.GOOD,
                eval_loss=10,
                position_fen="start"
            )
            for i, move in enumerate(moves_uci)
        ]

        opening_info = await analyzer.analyze_opening(moves_uci, move_analyses)

        assert opening_info.eco == "C50"
        assert "Italian" in opening_info.name
        assert len(opening_info.moves_uci) == 5
        assert opening_info.opening_accuracy > 0

    def test_add_opening_to_database(self, analyzer):
        """Test adding custom opening to database."""
        initial_size = analyzer.get_database_size()

        moves = ["e2e4", "a7a6"]  # Uncommon variation
        analyzer.add_opening_to_database(moves, "B00", "Test Opening")

        assert analyzer.get_database_size() == initial_size + 1

        # Verify retrieval
        eco, name = analyzer._identify_opening(moves)
        assert eco == "B00"
        assert name == "Test Opening"

    def test_database_size(self, analyzer):
        """Test database contains reasonable number of openings."""
        size = analyzer.get_database_size()
        assert size > 20  # Should have at least 20 common openings

    def test_common_opening_mistakes(self, analyzer):
        """Test retrieval of common opening mistakes."""
        mistakes = analyzer.get_common_opening_mistakes()

        assert isinstance(mistakes, list)
        assert len(mistakes) > 0

        # Check structure
        for mistake in mistakes:
            assert "mistake" in mistake
            assert "description" in mistake
            assert "severity" in mistake

    def test_opening_phase_moves_count(self, analyzer):
        """Test that opening phase is limited to 15 moves."""
        assert analyzer.opening_phase_moves == 15
