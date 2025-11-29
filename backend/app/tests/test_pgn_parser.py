"""
Unit tests for PGN parser service.

Tests the PGNParser utility functions.
"""

import pytest
import chess

from app.services.pgn_parser import PGNParser
from app.models.chess_com import ChessGame, GamePlayer, ParsedGame
from app.core.exceptions import ValidationException


# Sample PGN data
VALID_PGN = """[Event "Live Chess"]
[Site "Chess.com"]
[Date "2024.01.15"]
[Round "?"]
[White "player1"]
[Black "player2"]
[Result "1-0"]
[ECO "C50"]
[WhiteElo "1500"]
[BlackElo "1480"]
[TimeControl "600"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. d3 d6 6. Bg5 h6 7. Bh4 g5 8. Bg3 1-0
"""

INVALID_PGN = """[Event "Test"]
This is not valid PGN
"""

SHORT_GAME_PGN = """[Event "Short Game"]
[White "player1"]
[Black "player2"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
"""


class TestPGNParser:
    """Test suite for PGNParser."""

    def test_parse_valid_pgn(self):
        """Test parsing valid PGN string."""
        game = PGNParser.parse_pgn_string(VALID_PGN)

        assert game is not None
        assert isinstance(game, chess.pgn.Game)
        assert game.headers["Event"] == "Live Chess"
        assert game.headers["White"] == "player1"
        assert game.headers["Black"] == "player2"

    def test_parse_empty_pgn(self):
        """Test parsing empty PGN raises exception."""
        with pytest.raises(ValidationException) as exc_info:
            PGNParser.parse_pgn_string("")

        assert "empty" in str(exc_info.value).lower()

    def test_parse_invalid_pgn(self):
        """Test parsing invalid PGN raises exception."""
        with pytest.raises(ValidationException) as exc_info:
            PGNParser.parse_pgn_string(INVALID_PGN)

        assert "invalid" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()

    def test_extract_moves(self):
        """Test extracting moves from PGN."""
        game = PGNParser.parse_pgn_string(VALID_PGN)
        moves = PGNParser.extract_moves(game)

        assert isinstance(moves, list)
        assert len(moves) > 0
        assert moves[0] == "e4"
        assert moves[1] == "e5"
        assert all(isinstance(move, str) for move in moves)

    def test_extract_moves_short_game(self):
        """Test extracting moves from short game."""
        game = PGNParser.parse_pgn_string(SHORT_GAME_PGN)
        moves = PGNParser.extract_moves(game)

        assert len(moves) == 7  # 4 moves from white, 3 from black
        assert moves[0] == "e4"
        assert moves[-1] == "Qxf7#"

    def test_extract_headers(self):
        """Test extracting headers from PGN."""
        game = PGNParser.parse_pgn_string(VALID_PGN)
        headers = PGNParser.extract_headers(game)

        assert isinstance(headers, dict)
        assert "Event" in headers
        assert "White" in headers
        assert "Black" in headers
        assert headers["Event"] == "Live Chess"

    def test_get_result_from_pgn(self):
        """Test getting result from PGN."""
        game = PGNParser.parse_pgn_string(VALID_PGN)
        result = PGNParser.get_result_from_pgn(game)

        assert result == "1-0"

    def test_parse_chess_com_game(self):
        """Test parsing Chess.com game into ParsedGame."""
        chess_game = ChessGame(
            url="https://www.chess.com/game/live/12345678",
            pgn=VALID_PGN,
            time_control="600",
            end_time=1705329000,
            rated=True,
            uuid="test-game-123",
            time_class="rapid",
            rules="chess",
            white=GamePlayer(
                username="player1",
                rating=1500,
                result="win",
                uuid="player1-id",
            ),
            black=GamePlayer(
                username="player2",
                rating=1480,
                result="checkmated",
                uuid="player2-id",
            ),
        )

        parsed = PGNParser.parse_chess_com_game(chess_game)

        assert isinstance(parsed, ParsedGame)
        assert parsed.game_id == "test-game-123"
        assert parsed.white_username == "player1"
        assert parsed.black_username == "player2"
        assert parsed.white_rating == 1500
        assert parsed.black_rating == 1480
        assert parsed.time_class == "rapid"
        assert len(parsed.moves) > 0
        assert parsed.move_count == len(parsed.moves)

    def test_parse_chess_com_games_batch(self):
        """Test parsing multiple Chess.com games."""
        chess_game_1 = ChessGame(
            url="https://www.chess.com/game/live/1",
            pgn=VALID_PGN,
            time_control="600",
            end_time=1705329000,
            rated=True,
            uuid="game-1",
            time_class="rapid",
            rules="chess",
            white=GamePlayer(
                username="player1", rating=1500, result="win", uuid="p1"
            ),
            black=GamePlayer(
                username="player2", rating=1480, result="checkmated", uuid="p2"
            ),
        )

        chess_game_2 = ChessGame(
            url="https://www.chess.com/game/live/2",
            pgn=SHORT_GAME_PGN,
            time_control="180",
            end_time=1705329100,
            rated=True,
            uuid="game-2",
            time_class="blitz",
            rules="chess",
            white=GamePlayer(
                username="player3", rating=1600, result="win", uuid="p3"
            ),
            black=GamePlayer(
                username="player4", rating=1550, result="checkmated", uuid="p4"
            ),
        )

        parsed_games = PGNParser.parse_chess_com_games([chess_game_1, chess_game_2])

        assert len(parsed_games) == 2
        assert all(isinstance(g, ParsedGame) for g in parsed_games)

    def test_parse_chess_com_games_skip_invalid(self):
        """Test that batch parsing skips invalid games."""
        valid_game = ChessGame(
            url="https://www.chess.com/game/live/1",
            pgn=VALID_PGN,
            time_control="600",
            end_time=1705329000,
            rated=True,
            uuid="game-1",
            time_class="rapid",
            rules="chess",
            white=GamePlayer(
                username="player1", rating=1500, result="win", uuid="p1"
            ),
            black=GamePlayer(
                username="player2", rating=1480, result="checkmated", uuid="p2"
            ),
        )

        invalid_game = ChessGame(
            url="https://www.chess.com/game/live/2",
            pgn=INVALID_PGN,
            time_control="600",
            end_time=1705329000,
            rated=True,
            uuid="game-2",
            time_class="rapid",
            rules="chess",
            white=GamePlayer(
                username="player3", rating=1500, result="win", uuid="p3"
            ),
            black=GamePlayer(
                username="player4", rating=1480, result="checkmated", uuid="p4"
            ),
        )

        parsed_games = PGNParser.parse_chess_com_games([valid_game, invalid_game])

        # Should only have the valid game
        assert len(parsed_games) == 1
        assert parsed_games[0].game_id == "game-1"

    def test_get_opening_moves(self):
        """Test extracting opening moves."""
        game = PGNParser.parse_pgn_string(VALID_PGN)
        moves = PGNParser.extract_moves(game)

        opening = PGNParser.get_opening_moves(moves, num_moves=5)

        assert len(opening) == 5
        assert opening[0] == "e4"
        assert opening[1] == "e5"

    def test_get_opening_moves_short_game(self):
        """Test extracting opening moves from short game."""
        game = PGNParser.parse_pgn_string(SHORT_GAME_PGN)
        moves = PGNParser.extract_moves(game)

        opening = PGNParser.get_opening_moves(moves, num_moves=10)

        # Should return all available moves if less than requested
        assert len(opening) == len(moves)

    def test_validate_position_valid_fen(self):
        """Test validating valid FEN position."""
        valid_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        assert PGNParser.validate_position(valid_fen) is True

    def test_validate_position_invalid_fen(self):
        """Test validating invalid FEN position."""
        invalid_fen = "invalid fen string"
        assert PGNParser.validate_position(invalid_fen) is False

    def test_get_board_from_moves(self):
        """Test creating board from moves."""
        game = PGNParser.parse_pgn_string(SHORT_GAME_PGN)
        moves = PGNParser.extract_moves(game)

        board = PGNParser.get_board_from_moves(moves)

        assert isinstance(board, chess.Board)
        # After Qxf7# the game should be over
        assert board.is_checkmate()

    def test_get_board_from_invalid_moves(self):
        """Test that invalid moves raise exception."""
        invalid_moves = ["e4", "e5", "InvalidMove"]

        with pytest.raises(ValidationException) as exc_info:
            PGNParser.get_board_from_moves(invalid_moves)

        assert "invalid" in str(exc_info.value).lower()

    def test_get_position_after_moves(self):
        """Test getting position after specific number of moves."""
        game = PGNParser.parse_pgn_string(VALID_PGN)
        moves = PGNParser.extract_moves(game)

        board = PGNParser.get_position_after_moves(moves, 4)

        assert isinstance(board, chess.Board)
        # After 4 moves (2 full moves), we should have 1. e4 e5 2. Nf3 Nc6
        assert board.fullmove_number == 3  # Ready for move 3

    def test_get_position_after_invalid_move_number(self):
        """Test that invalid move number raises exception."""
        game = PGNParser.parse_pgn_string(VALID_PGN)
        moves = PGNParser.extract_moves(game)

        with pytest.raises(ValidationException):
            PGNParser.get_position_after_moves(moves, 0)

        with pytest.raises(ValidationException):
            PGNParser.get_position_after_moves(moves, len(moves) + 1)

    def test_filter_games_by_time_class(self):
        """Test filtering games by time class."""
        game1 = ParsedGame(
            game_id="1",
            url="http://test.com/1",
            pgn=VALID_PGN,
            time_control="600",
            time_class="rapid",
            rated=True,
            variant="chess",
            end_time=chess.pgn.read_game(chess.pgn.StringIO(VALID_PGN)),
            white_username="p1",
            white_rating=1500,
            white_result="win",
            black_username="p2",
            black_rating=1480,
            black_result="checkmated",
            moves=["e4", "e5"],
            move_count=2,
        )

        game2 = ParsedGame(
            game_id="2",
            url="http://test.com/2",
            pgn=VALID_PGN,
            time_control="180",
            time_class="blitz",
            rated=True,
            variant="chess",
            end_time=chess.pgn.read_game(chess.pgn.StringIO(VALID_PGN)),
            white_username="p3",
            white_rating=1600,
            white_result="win",
            black_username="p4",
            black_result="checkmated",
            black_rating=1550,
            moves=["d4", "d5"],
            move_count=2,
        )

        rapid_games = PGNParser.filter_games_by_time_class([game1, game2], "rapid")
        blitz_games = PGNParser.filter_games_by_time_class([game1, game2], "blitz")

        assert len(rapid_games) == 1
        assert rapid_games[0].game_id == "1"
        assert len(blitz_games) == 1
        assert blitz_games[0].game_id == "2"

    def test_get_game_statistics_empty(self):
        """Test statistics for empty game list."""
        stats = PGNParser.get_game_statistics([])

        assert stats["total_games"] == 0
        assert stats["average_moves"] == 0

    def test_get_game_statistics_with_games(self):
        """Test statistics calculation."""
        from datetime import datetime

        game1 = ParsedGame(
            game_id="1",
            url="http://test.com/1",
            pgn=VALID_PGN,
            time_control="600",
            time_class="rapid",
            rated=True,
            variant="chess",
            end_time=datetime.now(),
            white_username="p1",
            white_rating=1500,
            white_result="win",
            black_username="p2",
            black_rating=1480,
            black_result="checkmated",
            moves=["e4"] * 40,
            move_count=40,
        )

        game2 = ParsedGame(
            game_id="2",
            url="http://test.com/2",
            pgn=VALID_PGN,
            time_control="180",
            time_class="blitz",
            rated=True,
            variant="chess",
            end_time=datetime.now(),
            white_username="p3",
            white_rating=1600,
            white_result="win",
            black_username="p4",
            black_rating=1550,
            black_result="checkmated",
            moves=["d4"] * 60,
            move_count=60,
        )

        stats = PGNParser.get_game_statistics([game1, game2])

        assert stats["total_games"] == 2
        assert stats["average_moves"] == 50.0  # (40 + 60) / 2
        assert stats["total_moves"] == 100
        assert "rapid" in stats["time_classes"]
        assert "blitz" in stats["time_classes"]
        assert stats["time_classes"]["rapid"] == 1
        assert stats["time_classes"]["blitz"] == 1
