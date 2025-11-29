"""
Tactical pattern detection.

Identifies chess tactical patterns like forks, pins, skewers, and hanging pieces.
"""

import chess
from typing import List, Optional, Dict, Set
from app.models.chess_models import TacticalPattern, PatternType


class TacticalPatternDetector:
    """
    Detect tactical patterns in chess positions.

    Identifies common tactical motifs including:
    - Hanging pieces (undefended pieces under attack)
    - Forks (one piece attacking two or more valuable pieces)
    - Pins (piece cannot move without exposing more valuable piece)
    - Skewers (forcing valuable piece to move, exposing less valuable piece)
    - Back rank weaknesses
    - Discovered attacks
    """

    # Piece values in centipawns (standard values)
    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 20000,
    }

    def __init__(self):
        """Initialize tactical pattern detector."""
        self.patterns_cache: Dict[str, List[TacticalPattern]] = {}

    def detect_all_patterns(
        self,
        board: chess.Board,
        last_move: Optional[chess.Move] = None,
    ) -> List[TacticalPattern]:
        """
        Detect all tactical patterns in the current position.

        Args:
            board: Current chess position
            last_move: The move that was just played (optional)

        Returns:
            List of detected tactical patterns
        """
        patterns = []

        # Detect hanging pieces
        hanging = self.detect_hanging_pieces(board)
        patterns.extend(hanging)

        # Detect forks
        if last_move:
            fork = self.detect_fork(board, last_move)
            if fork:
                patterns.append(fork)

        # Detect pins
        pins = self.detect_pins(board)
        patterns.extend(pins)

        # Detect skewers
        skewers = self.detect_skewers(board)
        patterns.extend(skewers)

        # Detect back rank weakness
        back_rank = self.detect_back_rank_weakness(board)
        if back_rank:
            patterns.append(back_rank)

        # Detect discovered attacks
        if last_move:
            discovered = self.detect_discovered_attack(board, last_move)
            if discovered:
                patterns.append(discovered)

        # Detect trapped pieces
        trapped = self.detect_trapped_pieces(board)
        patterns.extend(trapped)

        return patterns

    def detect_hanging_pieces(self, board: chess.Board) -> List[TacticalPattern]:
        """
        Detect hanging pieces (undefended pieces under attack).

        Args:
            board: Chess position

        Returns:
            List of hanging piece patterns
        """
        hanging_patterns = []

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece or piece.color != board.turn:
                continue

            # Count attackers and defenders
            attackers = board.attackers(not board.turn, square)
            defenders = board.attackers(board.turn, square)

            # Piece is hanging if attacked and not defended
            if len(attackers) > 0 and len(defenders) == 0:
                # Skip pawns unless they're valuable captures
                if piece.piece_type == chess.PAWN:
                    # Check if pawn is advanced or creates threat
                    rank = chess.square_rank(square)
                    if (board.turn == chess.WHITE and rank < 5) or \
                       (board.turn == chess.BLACK and rank > 2):
                        continue  # Skip non-advanced pawns

                value = self.PIECE_VALUES[piece.piece_type]
                severity = self._calculate_severity(value)

                hanging_patterns.append(TacticalPattern(
                    pattern_type=PatternType.HANGING_PIECE,
                    severity=severity,
                    pieces_involved=[piece.symbol()],
                    squares=[chess.square_name(square)],
                    centipawn_value=value,
                    description=f"{piece.symbol()} on {chess.square_name(square)} is hanging"
                ))

            # Also detect if piece is hanging due to insufficient defense
            elif len(attackers) > len(defenders):
                # Calculate material exchange
                attacker_values = [
                    self.PIECE_VALUES[board.piece_at(sq).piece_type]
                    for sq in attackers if board.piece_at(sq)
                ]
                defender_values = [
                    self.PIECE_VALUES[board.piece_at(sq).piece_type]
                    for sq in defenders if board.piece_at(sq)
                ]

                # Simplistic calculation: if losing material on exchange
                if attacker_values and defender_values:
                    min_attacker = min(attacker_values)
                    piece_value = self.PIECE_VALUES[piece.piece_type]

                    if piece_value > min_attacker:
                        # Piece can be captured favorably
                        loss = piece_value - min_attacker
                        if loss >= 100:  # At least a pawn
                            hanging_patterns.append(TacticalPattern(
                                pattern_type=PatternType.HANGING_PIECE,
                                severity=self._calculate_severity(loss),
                                pieces_involved=[piece.symbol()],
                                squares=[chess.square_name(square)],
                                centipawn_value=loss,
                                description=f"{piece.symbol()} on {chess.square_name(square)} "
                                           f"loses material on exchange"
                            ))

        return hanging_patterns

    def detect_fork(
        self,
        board: chess.Board,
        last_move: chess.Move
    ) -> Optional[TacticalPattern]:
        """
        Detect if the last move created a fork.

        Args:
            board: Current position (after the move)
            last_move: The move that was played

        Returns:
            Fork pattern if detected, None otherwise
        """
        attacking_square = last_move.to_square
        attacking_piece = board.piece_at(attacking_square)

        if not attacking_piece:
            return None

        # Get all squares attacked by the moved piece
        attacks = board.attacks(attacking_square)

        # Find valuable targets (pieces worth defending)
        valuable_targets = []
        target_squares = []

        for target_square in attacks:
            target_piece = board.piece_at(target_square)
            if target_piece and target_piece.color != attacking_piece.color:
                value = self.PIECE_VALUES[target_piece.piece_type]

                # Consider pieces worth at least a knight
                if value >= self.PIECE_VALUES[chess.KNIGHT]:
                    valuable_targets.append(target_piece.symbol())
                    target_squares.append(chess.square_name(target_square))

        # Fork if attacking 2+ valuable pieces
        if len(valuable_targets) >= 2:
            total_value = sum(
                self.PIECE_VALUES[board.piece_at(chess.parse_square(sq)).piece_type]
                for sq in target_squares
                if board.piece_at(chess.parse_square(sq))
            )

            return TacticalPattern(
                pattern_type=PatternType.KNIGHT_FORK if attacking_piece.piece_type == chess.KNIGHT
                            else PatternType.FORK,
                severity="high",
                pieces_involved=[attacking_piece.symbol()] + valuable_targets,
                squares=[chess.square_name(attacking_square)] + target_squares,
                centipawn_value=total_value,
                description=f"{attacking_piece.symbol()} forks {len(valuable_targets)} pieces"
            )

        return None

    def detect_pins(self, board: chess.Board) -> List[TacticalPattern]:
        """
        Detect pinned pieces in the position.

        Args:
            board: Chess position

        Returns:
            List of pin patterns
        """
        pins = []
        king_square = board.king(board.turn)

        if king_square is None:
            return pins

        # Check each enemy piece that can pin (bishops, rooks, queens)
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece or piece.color == board.turn:
                continue

            if piece.piece_type not in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
                continue

            # Check if this piece creates a pin to the king
            pin_info = self._check_pin_ray(board, square, king_square, piece.piece_type)
            if pin_info:
                pins.append(pin_info)

        return pins

    def _check_pin_ray(
        self,
        board: chess.Board,
        attacker_square: int,
        king_square: int,
        piece_type: int,
    ) -> Optional[TacticalPattern]:
        """
        Check if attacker pins a piece to the king along a ray.

        Args:
            board: Chess position
            attacker_square: Square of potential pinning piece
            king_square: Square of the king
            piece_type: Type of the pinning piece

        Returns:
            Pin pattern if found, None otherwise
        """
        # Determine valid directions for piece type
        if piece_type == chess.BISHOP:
            # Diagonal rays only
            ray_attacks = chess.BB_DIAG_ATTACKS[attacker_square][0]
        elif piece_type == chess.ROOK:
            # Horizontal and vertical rays only
            ray_attacks = chess.BB_RANK_ATTACKS[attacker_square][0] | \
                         chess.BB_FILE_ATTACKS[attacker_square][0]
        elif piece_type == chess.QUEEN:
            # All rays
            ray_attacks = chess.BB_DIAG_ATTACKS[attacker_square][0] | \
                         chess.BB_RANK_ATTACKS[attacker_square][0] | \
                         chess.BB_FILE_ATTACKS[attacker_square][0]
        else:
            return None

        # Check if king is on a ray from attacker
        if not (chess.BB_SQUARES[king_square] & ray_attacks):
            return None

        # Get squares between attacker and king
        between = chess.between(attacker_square, king_square)

        # Find pieces between attacker and king
        pieces_between = []
        for sq in chess.scan_forward(between):
            piece = board.piece_at(sq)
            if piece:
                pieces_between.append((sq, piece))

        # Pin exists if exactly one piece between attacker and king
        if len(pieces_between) == 1:
            pinned_square, pinned_piece = pieces_between[0]

            # Verify it's our piece
            if pinned_piece.color == board.turn:
                attacker_piece = board.piece_at(attacker_square)
                value = self.PIECE_VALUES[pinned_piece.piece_type]

                return TacticalPattern(
                    pattern_type=PatternType.PIN,
                    severity=self._calculate_severity(value),
                    pieces_involved=[attacker_piece.symbol(), pinned_piece.symbol()],
                    squares=[
                        chess.square_name(attacker_square),
                        chess.square_name(pinned_square),
                        chess.square_name(king_square)
                    ],
                    centipawn_value=value,
                    description=f"{pinned_piece.symbol()} on {chess.square_name(pinned_square)} "
                               f"is pinned to king"
                )

        return None

    def detect_skewers(self, board: chess.Board) -> List[TacticalPattern]:
        """
        Detect skewer patterns.

        A skewer is like a pin in reverse: a valuable piece is attacked and must move,
        exposing a less valuable piece behind it.

        Args:
            board: Chess position

        Returns:
            List of skewer patterns
        """
        skewers = []

        # Check each enemy long-range piece
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece or piece.color == board.turn:
                continue

            if piece.piece_type not in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
                continue

            # Check each attacked square
            for target_square in board.attacks(square):
                target_piece = board.piece_at(target_square)
                if not target_piece or target_piece.color != board.turn:
                    continue

                # Check if there's a piece behind the target on the same ray
                skewer_info = self._check_skewer_ray(
                    board, square, target_square, piece.piece_type
                )
                if skewer_info:
                    skewers.append(skewer_info)

        return skewers

    def _check_skewer_ray(
        self,
        board: chess.Board,
        attacker_square: int,
        target_square: int,
        piece_type: int,
    ) -> Optional[TacticalPattern]:
        """Check for skewer along a ray."""
        # Get ray direction from attacker through target
        ray_beyond = chess.ray(attacker_square, target_square)

        # Remove attacker and target squares
        ray_beyond &= ~chess.BB_SQUARES[attacker_square]
        ray_beyond &= ~chess.BB_SQUARES[target_square]

        # Find next piece on the ray
        for sq in chess.scan_forward(ray_beyond & chess.BB_SQUARES[target_square:]):
            piece = board.piece_at(sq)
            if piece and piece.color == board.turn:
                # Found a skewer if target is more valuable
                target_piece = board.piece_at(target_square)
                target_value = self.PIECE_VALUES[target_piece.piece_type]
                behind_value = self.PIECE_VALUES[piece.piece_type]

                if target_value > behind_value:
                    return TacticalPattern(
                        pattern_type=PatternType.SKEWER,
                        severity="high",
                        pieces_involved=[target_piece.symbol(), piece.symbol()],
                        squares=[
                            chess.square_name(target_square),
                            chess.square_name(sq)
                        ],
                        centipawn_value=behind_value,
                        description=f"Skewer: {target_piece.symbol()} must move, exposing "
                                   f"{piece.symbol()}"
                    )
            elif piece:
                break  # Different color, stop searching

        return None

    def detect_back_rank_weakness(self, board: chess.Board) -> Optional[TacticalPattern]:
        """
        Detect back rank mate weaknesses.

        Args:
            board: Chess position

        Returns:
            Back rank weakness pattern if detected
        """
        king_square = board.king(board.turn)
        if king_square is None:
            return None

        king_rank = chess.square_rank(king_square)

        # Check if king is on back rank
        if (board.turn == chess.WHITE and king_rank != 0) or \
           (board.turn == chess.BLACK and king_rank != 7):
            return None

        # Check if king is trapped by its own pieces (no escape squares)
        escape_squares = list(board.attacks(king_square))
        can_escape = False

        for escape_sq in escape_squares:
            escape_rank = chess.square_rank(escape_sq)

            # Can escape if square is not attacked and not blocked by own pieces
            if not board.is_attacked_by(not board.turn, escape_sq):
                piece_on_escape = board.piece_at(escape_sq)
                if not piece_on_escape or piece_on_escape.color != board.turn:
                    can_escape = True
                    break

        if not can_escape:
            # Check if enemy has rook or queen that can attack back rank
            enemy_has_major_piece = False
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.color != board.turn:
                    if piece.piece_type in [chess.ROOK, chess.QUEEN]:
                        enemy_has_major_piece = True
                        break

            if enemy_has_major_piece:
                return TacticalPattern(
                    pattern_type=PatternType.BACK_RANK_WEAKNESS,
                    severity="high",
                    pieces_involved=["K"],
                    squares=[chess.square_name(king_square)],
                    centipawn_value=500,  # Significant weakness
                    description="King has back rank mate vulnerability"
                )

        return None

    def detect_discovered_attack(
        self,
        board: chess.Board,
        last_move: chess.Move
    ) -> Optional[TacticalPattern]:
        """
        Detect discovered attacks from the last move.

        Args:
            board: Current position
            last_move: Move that was played

        Returns:
            Discovered attack pattern if found
        """
        # TODO: This is complex to implement properly
        # Would require analyzing what piece was blocking what attack
        # For MVP, returning None - can implement in future iteration
        return None

    def detect_trapped_pieces(self, board: chess.Board) -> List[TacticalPattern]:
        """
        Detect pieces that are trapped with no good squares.

        Args:
            board: Chess position

        Returns:
            List of trapped piece patterns
        """
        trapped = []

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece or piece.color != board.turn:
                continue

            # Skip king and pawns
            if piece.piece_type in [chess.KING, chess.PAWN]:
                continue

            # Get all legal moves for this piece
            piece_moves = [
                move for move in board.legal_moves
                if move.from_square == square
            ]

            # Check if all moves lose material or are blocked
            if len(piece_moves) <= 2:  # Very limited mobility
                # Check if all available squares are attacked
                all_squares_attacked = all(
                    board.is_attacked_by(not board.turn, move.to_square)
                    for move in piece_moves
                )

                if all_squares_attacked:
                    value = self.PIECE_VALUES[piece.piece_type]
                    trapped.append(TacticalPattern(
                        pattern_type=PatternType.TRAPPED_PIECE,
                        severity=self._calculate_severity(value),
                        pieces_involved=[piece.symbol()],
                        squares=[chess.square_name(square)],
                        centipawn_value=value,
                        description=f"{piece.symbol()} on {chess.square_name(square)} is trapped"
                    ))

        return trapped

    def _calculate_severity(self, centipawn_value: int) -> str:
        """
        Calculate severity based on centipawn value.

        Args:
            centipawn_value: Material value in centipawns

        Returns:
            Severity string: "low", "medium", or "high"
        """
        if centipawn_value >= 500:  # Rook or more
            return "high"
        elif centipawn_value >= 300:  # Minor piece
            return "medium"
        else:
            return "low"
