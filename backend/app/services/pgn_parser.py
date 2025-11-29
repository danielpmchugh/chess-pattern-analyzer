"""
PGN (Portable Game Notation) parsing utilities.

This module provides functions to parse PGN data from Chess.com games
using the python-chess library and extract relevant game information.
"""

import io
from datetime import datetime
from typing import List, Optional, Dict, Any

import chess.pgn

from app.models.chess_com import ChessGame, ParsedGame
from app.core.logging import get_logger
from app.core.exceptions import ValidationException

logger = get_logger(__name__)


class PGNParser:
    """
    Parser for PGN (Portable Game Notation) data.

    Uses python-chess library to parse and validate PGN strings,
    extracting moves, headers, and game metadata.
    """

    @staticmethod
    def parse_pgn_string(pgn_string: str) -> chess.pgn.Game:
        """
        Parse a PGN string into a chess.pgn.Game object.

        Args:
            pgn_string: PGN notation string

        Returns:
            chess.pgn.Game object

        Raises:
            ValidationException: If PGN is invalid or cannot be parsed
        """
        if not pgn_string or not pgn_string.strip():
            raise ValidationException(
                field="pgn",
                value=pgn_string,
                reason="PGN string is empty",
            )

        try:
            # Parse PGN from string
            pgn_io = io.StringIO(pgn_string)
            game = chess.pgn.read_game(pgn_io)

            if game is None:
                raise ValidationException(
                    field="pgn",
                    value=pgn_string[:100],  # Truncate for logging
                    reason="Could not parse PGN - invalid format",
                )

            return game

        except Exception as e:
            logger.error(f"PGN parsing error: {e}")
            raise ValidationException(
                field="pgn",
                value=pgn_string[:100],
                reason=f"PGN parsing failed: {str(e)}",
            )

    @staticmethod
    def extract_moves(game: chess.pgn.Game) -> List[str]:
        """
        Extract moves from a chess.pgn.Game object.

        Args:
            game: Parsed chess.pgn.Game object

        Returns:
            List of moves in Standard Algebraic Notation (SAN)
        """
        moves = []
        board = game.board()

        for move in game.mainline_moves():
            san = board.san(move)
            moves.append(san)
            board.push(move)

        return moves

    @staticmethod
    def extract_headers(game: chess.pgn.Game) -> Dict[str, str]:
        """
        Extract headers from a PGN game.

        Args:
            game: Parsed chess.pgn.Game object

        Returns:
            Dictionary of header key-value pairs
        """
        headers = {}
        for key, value in game.headers.items():
            headers[key] = value
        return headers

    @staticmethod
    def get_result_from_pgn(game: chess.pgn.Game) -> str:
        """
        Extract game result from PGN headers.

        Args:
            game: Parsed chess.pgn.Game object

        Returns:
            Result string (e.g., "1-0", "0-1", "1/2-1/2", "*")
        """
        return game.headers.get("Result", "*")

    @staticmethod
    def parse_chess_com_game(chess_game: ChessGame) -> ParsedGame:
        """
        Parse a Chess.com game into a normalized ParsedGame model.

        Args:
            chess_game: ChessGame model from Chess.com API

        Returns:
            ParsedGame model with parsed data

        Raises:
            ValidationException: If PGN parsing fails
        """
        try:
            # Parse PGN
            game = PGNParser.parse_pgn_string(chess_game.pgn)

            # Extract moves
            moves = PGNParser.extract_moves(game)

            # Convert timestamp to datetime
            end_time = datetime.fromtimestamp(chess_game.end_time)

            # Create ParsedGame
            parsed = ParsedGame(
                game_id=chess_game.uuid,
                url=str(chess_game.url),
                pgn=chess_game.pgn,
                time_control=chess_game.time_control,
                time_class=chess_game.time_class,
                rated=chess_game.rated,
                variant=chess_game.rules,
                end_time=end_time,
                white_username=chess_game.white.username,
                white_rating=chess_game.white.rating,
                white_result=chess_game.white.result,
                black_username=chess_game.black.username,
                black_rating=chess_game.black.rating,
                black_result=chess_game.black.result,
                tournament_url=str(chess_game.tournament) if chess_game.tournament else None,
                moves=moves,
                move_count=len(moves),
            )

            logger.debug(
                f"Parsed game {parsed.game_id}: {len(moves)} moves, "
                f"{parsed.white_username} vs {parsed.black_username}"
            )

            return parsed

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error parsing Chess.com game {chess_game.uuid}: {e}")
            raise ValidationException(
                field="chess_game",
                value=chess_game.uuid,
                reason=f"Failed to parse Chess.com game: {str(e)}",
            )

    @staticmethod
    def parse_chess_com_games(chess_games: List[ChessGame]) -> List[ParsedGame]:
        """
        Parse multiple Chess.com games.

        Args:
            chess_games: List of ChessGame models

        Returns:
            List of ParsedGame models (skips games that fail to parse)
        """
        parsed_games = []
        failed_count = 0

        for chess_game in chess_games:
            try:
                parsed = PGNParser.parse_chess_com_game(chess_game)
                parsed_games.append(parsed)
            except Exception as e:
                failed_count += 1
                logger.warning(
                    f"Skipping game {chess_game.uuid} due to parsing error: {e}"
                )

        if failed_count > 0:
            logger.warning(
                f"Failed to parse {failed_count}/{len(chess_games)} games"
            )

        logger.info(
            f"Successfully parsed {len(parsed_games)}/{len(chess_games)} games"
        )

        return parsed_games

    @staticmethod
    def get_opening_moves(moves: List[str], num_moves: int = 10) -> List[str]:
        """
        Extract opening moves from a game.

        Args:
            moves: List of moves in SAN
            num_moves: Number of opening moves to extract

        Returns:
            List of opening moves
        """
        return moves[:num_moves]

    @staticmethod
    def validate_position(fen: str) -> bool:
        """
        Validate a FEN position string.

        Args:
            fen: FEN notation string

        Returns:
            True if valid, False otherwise
        """
        try:
            board = chess.Board(fen)
            return board.is_valid()
        except Exception:
            return False

    @staticmethod
    def get_board_from_moves(moves: List[str]) -> chess.Board:
        """
        Create a chess board from a list of moves.

        Args:
            moves: List of moves in SAN

        Returns:
            chess.Board object at the final position

        Raises:
            ValidationException: If moves are invalid
        """
        board = chess.Board()

        try:
            for i, move_san in enumerate(moves):
                move = board.parse_san(move_san)
                board.push(move)

            return board

        except Exception as e:
            raise ValidationException(
                field="moves",
                value=f"Move {i + 1}: {move_san}",
                reason=f"Invalid move: {str(e)}",
            )

    @staticmethod
    def get_position_after_moves(
        moves: List[str],
        move_number: int,
    ) -> chess.Board:
        """
        Get board position after a specific number of moves.

        Args:
            moves: List of moves in SAN
            move_number: Number of moves to play (1-indexed)

        Returns:
            chess.Board at the specified position

        Raises:
            ValidationException: If move_number is invalid or moves fail
        """
        if move_number < 1 or move_number > len(moves):
            raise ValidationException(
                field="move_number",
                value=move_number,
                reason=f"Move number must be between 1 and {len(moves)}",
            )

        return PGNParser.get_board_from_moves(moves[:move_number])

    @staticmethod
    def filter_games_by_time_class(
        games: List[ParsedGame],
        time_class: str,
    ) -> List[ParsedGame]:
        """
        Filter games by time control class.

        Args:
            games: List of ParsedGame objects
            time_class: Time class to filter (bullet, blitz, rapid, daily)

        Returns:
            Filtered list of games
        """
        return [
            game for game in games
            if game.time_class.lower() == time_class.lower()
        ]

    @staticmethod
    def filter_games_by_result(
        games: List[ParsedGame],
        username: str,
        result_type: str,
    ) -> List[ParsedGame]:
        """
        Filter games by result for a specific player.

        Args:
            games: List of ParsedGame objects
            username: Username to check results for
            result_type: Result type (win, loss, draw)

        Returns:
            Filtered list of games
        """
        username = username.lower()
        filtered = []

        for game in games:
            is_white = game.white_username.lower() == username
            is_black = game.black_username.lower() == username

            if not (is_white or is_black):
                continue

            result = game.white_result if is_white else game.black_result

            if result_type.lower() == "win" and "win" in result.lower():
                filtered.append(game)
            elif result_type.lower() == "loss" and any(
                x in result.lower() for x in ["lose", "resigned", "timeout", "checkmated"]
            ):
                filtered.append(game)
            elif result_type.lower() == "draw" and any(
                x in result.lower() for x in ["draw", "stalemate", "repetition", "insufficient"]
            ):
                filtered.append(game)

        return filtered

    @staticmethod
    def get_game_statistics(games: List[ParsedGame]) -> Dict[str, Any]:
        """
        Calculate statistics from a list of games.

        Args:
            games: List of ParsedGame objects

        Returns:
            Dictionary with game statistics
        """
        if not games:
            return {
                "total_games": 0,
                "time_classes": {},
                "average_moves": 0,
                "total_moves": 0,
            }

        time_classes = {}
        total_moves = 0

        for game in games:
            # Count time classes
            time_class = game.time_class
            time_classes[time_class] = time_classes.get(time_class, 0) + 1

            # Sum moves
            total_moves += game.move_count

        avg_moves = total_moves / len(games) if games else 0

        return {
            "total_games": len(games),
            "time_classes": time_classes,
            "average_moves": round(avg_moves, 1),
            "total_moves": total_moves,
        }
