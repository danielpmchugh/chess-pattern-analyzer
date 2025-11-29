# Task: ENGINE-001 - Pattern Detection Core

**Status**: `todo`
**Priority**: Critical
**Assigned Agent**: chess-engine-developer (to be created)
**Estimated Effort**: 3-4 days
**Dependencies**: DATA-001 (for data models)

## Objective

Build the core pattern recognition engine using python-chess and Stockfish to detect opening mistakes, tactical patterns, blunders, and position evaluation issues across a player's games.

## Success Criteria

1. Detect 90%+ of tactical blunders (> 200 centipawn loss)
2. Identify common opening deviations and mistakes
3. Recognize standard tactical motifs (forks, pins, skewers)
4. Process a game in under 2 seconds average
5. Support batch processing of 100 games
6. Provide position evaluations with explanations

## Technical Approach

### 1. Engine Configuration

```python
import chess
import chess.engine
import chess.pgn
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass
import asyncio
from pathlib import Path

@dataclass
class EngineConfig:
    """Stockfish engine configuration"""
    path: str = "/usr/local/bin/stockfish"  # Azure Container path
    depth: int = 18  # Analysis depth
    time_limit: float = 0.5  # Seconds per position
    threads: int = 2  # CPU threads
    hash_size: int = 256  # MB
    multipv: int = 3  # Top 3 moves

class StockfishManager:
    """Manage Stockfish engine lifecycle"""

    def __init__(self, config: EngineConfig):
        self.config = config
        self.engine = None

    async def __aenter__(self):
        self.engine = await chess.engine.popen_uci(self.config.path)
        await self.engine.configure({
            "Threads": self.config.threads,
            "Hash": self.config.hash_size,
            "MultiPV": self.config.multipv
        })
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.engine:
            await self.engine.quit()

    async def analyze_position(
        self,
        board: chess.Board,
        time_limit: Optional[float] = None
    ) -> chess.engine.AnalysisResult:
        """Analyze single position"""
        limit = chess.engine.Limit(
            time=time_limit or self.config.time_limit,
            depth=self.config.depth
        )
        return await self.engine.analysis(board, limit)
```

### 2. Pattern Detection Engine

```python
from enum import Enum
from abc import ABC, abstractmethod

class PatternDetector(ABC):
    """Base class for pattern detectors"""

    @abstractmethod
    async def detect(
        self,
        board: chess.Board,
        move: chess.Move,
        evaluation: chess.engine.PovScore
    ) -> Optional[Dict[str, Any]]:
        pass

class TacticalPatternDetector(PatternDetector):
    """Detect tactical patterns"""

    PATTERNS = {
        'hanging_piece': {'threshold': 100},
        'fork': {'piece_types': [chess.KNIGHT, chess.QUEEN, chess.PAWN]},
        'pin': {'types': ['absolute', 'relative']},
        'skewer': {'min_value': 300},
        'discovered_attack': {'check_required': False},
        'back_rank_mate': {'pieces_required': [chess.ROOK, chess.QUEEN]}
    }

    async def detect(
        self,
        board: chess.Board,
        move: chess.Move,
        evaluation: chess.engine.PovScore
    ) -> Optional[Dict[str, Any]]:
        """Detect tactical patterns in position"""
        patterns_found = []

        # Check for hanging pieces
        if self._has_hanging_piece(board):
            patterns_found.append({
                'type': 'hanging_piece',
                'severity': 'high',
                'pieces': self._get_hanging_pieces(board)
            })

        # Check for forks
        if self._is_fork(board, move):
            patterns_found.append({
                'type': 'fork',
                'attacking_piece': board.piece_at(move.to_square),
                'targets': self._get_fork_targets(board, move)
            })

        # Check for pins
        pins = self._find_pins(board)
        if pins:
            patterns_found.append({
                'type': 'pin',
                'pins': pins
            })

        # Check for back rank weakness
        if self._has_back_rank_weakness(board):
            patterns_found.append({
                'type': 'back_rank_weakness',
                'color': board.turn
            })

        return patterns_found if patterns_found else None

    def _has_hanging_piece(self, board: chess.Board) -> bool:
        """Check if there are undefended pieces"""
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == board.turn:
                if not board.is_attacked_by(board.turn, square):
                    # Check if piece is attacked
                    if board.is_attacked_by(not board.turn, square):
                        return True
        return False

    def _get_hanging_pieces(self, board: chess.Board) -> List[Dict]:
        """Get list of hanging pieces"""
        hanging = []
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == board.turn:
                attackers = board.attackers(not board.turn, square)
                defenders = board.attackers(board.turn, square)
                if len(attackers) > len(defenders):
                    hanging.append({
                        'square': chess.square_name(square),
                        'piece': piece.symbol(),
                        'value': self._piece_value(piece.piece_type)
                    })
        return hanging

    def _is_fork(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a fork"""
        board_copy = board.copy()
        board_copy.push(move)

        attacking_square = move.to_square
        attacked_squares = board_copy.attacks(attacking_square)

        valuable_targets = 0
        for square in attacked_squares:
            target = board_copy.piece_at(square)
            if target and target.color != board_copy.turn:
                if self._piece_value(target.piece_type) >= 3:
                    valuable_targets += 1

        return valuable_targets >= 2

    def _find_pins(self, board: chess.Board) -> List[Dict]:
        """Find all pins in the position"""
        pins = []
        king_square = board.king(board.turn)

        # Check for pins from each enemy piece
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color != board.turn:
                if piece.piece_type in [chess.ROOK, chess.BISHOP, chess.QUEEN]:
                    # Check if piece attacks king through another piece
                    pin = self._check_pin_ray(board, square, king_square)
                    if pin:
                        pins.append(pin)

        return pins

    def _piece_value(self, piece_type: int) -> int:
        """Get piece value in centipawns"""
        values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }
        return values.get(piece_type, 0)
```

### 3. Opening Mistake Detector

```python
import chess.polyglot

class OpeningAnalyzer:
    """Analyze opening phase and detect mistakes"""

    def __init__(self, opening_book_path: Optional[str] = None):
        self.book_path = opening_book_path
        self.eco_database = self._load_eco_database()

    def _load_eco_database(self) -> Dict[str, Dict]:
        """Load ECO opening classifications"""
        # Simplified ECO database
        return {
            "e4 e5": {"eco": "C20", "name": "King's Pawn Game"},
            "d4 Nf6": {"eco": "A45", "name": "Indian Defense"},
            "e4 c5": {"eco": "B20", "name": "Sicilian Defense"},
            # ... more openings
        }

    async def analyze_opening(
        self,
        game: chess.pgn.Game,
        engine: StockfishManager
    ) -> Dict[str, Any]:
        """Analyze opening phase of the game"""
        board = game.board()
        opening_moves = []
        mistakes = []

        node = game
        move_num = 0

        # Analyze first 15 moves (opening phase)
        while node.variations and move_num < 15:
            move = node.variations[0].move
            move_num += 1

            # Get evaluation before move
            eval_before = await self._get_evaluation(board, engine)

            # Make move
            board.push(move)

            # Get evaluation after move
            eval_after = await self._get_evaluation(board, engine)

            # Check for opening mistake
            if self._is_opening_mistake(eval_before, eval_after):
                best_move = await self._get_best_move(board, engine)
                mistakes.append({
                    'move_number': move_num,
                    'played_move': move.uci(),
                    'best_move': best_move.uci() if best_move else None,
                    'eval_loss': self._calculate_eval_loss(eval_before, eval_after),
                    'position_fen': board.fen()
                })

            opening_moves.append(move.uci())
            node = node.variations[0]

        # Identify opening
        opening_key = " ".join(opening_moves[:4])
        opening_info = self._identify_opening(opening_key)

        return {
            'eco': opening_info.get('eco'),
            'name': opening_info.get('name'),
            'moves': opening_moves,
            'mistakes': mistakes,
            'deviation_point': self._find_theory_deviation(opening_moves)
        }

    async def _get_evaluation(
        self,
        board: chess.Board,
        engine: StockfishManager
    ) -> float:
        """Get position evaluation in centipawns"""
        info = await engine.analyze_position(board)
        score = info.score()
        if score.is_mate():
            return 10000 if score.mate() > 0 else -10000
        return score.score()

    def _is_opening_mistake(
        self,
        eval_before: float,
        eval_after: float,
        threshold: float = 50
    ) -> bool:
        """Check if move is an opening mistake"""
        eval_loss = eval_after - eval_before
        return abs(eval_loss) > threshold

    def _identify_opening(self, move_sequence: str) -> Dict[str, str]:
        """Identify opening from move sequence"""
        # Check exact match first
        if move_sequence in self.eco_database:
            return self.eco_database[move_sequence]

        # Check partial matches
        for key in sorted(self.eco_database.keys(), key=len, reverse=True):
            if move_sequence.startswith(key):
                return self.eco_database[key]

        return {"eco": "A00", "name": "Unknown Opening"}
```

### 4. Blunder Detection

```python
class BlunderDetector:
    """Detect blunders and critical mistakes"""

    THRESHOLDS = {
        'inaccuracy': 50,  # 0.5 pawns
        'mistake': 100,     # 1 pawn
        'blunder': 200,     # 2 pawns
        'critical_blunder': 400  # 4 pawns
    }

    async def analyze_move(
        self,
        board_before: chess.Board,
        move: chess.Move,
        engine: StockfishManager
    ) -> Dict[str, Any]:
        """Analyze single move for blunders"""

        # Get evaluation before move
        analysis_before = await engine.analyze_position(board_before)
        eval_before = self._score_to_cp(analysis_before.score())

        # Make the move
        board_after = board_before.copy()
        board_after.push(move)

        # Get evaluation after move
        analysis_after = await engine.analyze_position(board_after)
        eval_after = self._score_to_cp(analysis_after.score())

        # Get best move
        best_moves = await self._get_top_moves(board_before, engine, n=3)

        # Calculate evaluation loss
        best_eval = self._score_to_cp(best_moves[0]['score']) if best_moves else eval_before
        eval_loss = abs(best_eval - eval_after)

        # Classify the move
        classification = self._classify_move(eval_loss)

        # Detect specific blunder types
        blunder_type = await self._identify_blunder_type(
            board_before,
            move,
            board_after,
            eval_loss
        )

        return {
            'move': move.uci(),
            'san': board_before.san(move),
            'classification': classification,
            'eval_before': eval_before,
            'eval_after': eval_after,
            'best_move': best_moves[0]['move'] if best_moves else None,
            'best_eval': best_eval,
            'eval_loss': eval_loss,
            'blunder_type': blunder_type,
            'alternatives': best_moves[:3]
        }

    def _score_to_cp(self, score: chess.engine.PovScore) -> float:
        """Convert score to centipawns"""
        if score.is_mate():
            return 10000 if score.mate() > 0 else -10000
        return score.score()

    def _classify_move(self, eval_loss: float) -> str:
        """Classify move based on evaluation loss"""
        if eval_loss < self.THRESHOLDS['inaccuracy']:
            return 'good'
        elif eval_loss < self.THRESHOLDS['mistake']:
            return 'inaccuracy'
        elif eval_loss < self.THRESHOLDS['blunder']:
            return 'mistake'
        elif eval_loss < self.THRESHOLDS['critical_blunder']:
            return 'blunder'
        else:
            return 'critical_blunder'

    async def _identify_blunder_type(
        self,
        board_before: chess.Board,
        move: chess.Move,
        board_after: chess.Board,
        eval_loss: float
    ) -> Optional[str]:
        """Identify specific type of blunder"""

        if eval_loss < self.THRESHOLDS['blunder']:
            return None

        # Check for hanging piece
        if self._leaves_piece_hanging(board_after):
            return 'hanging_piece'

        # Check for missed checkmate
        if self._missed_checkmate(board_before):
            return 'missed_checkmate'

        # Check for allowing tactics
        if self._allows_tactic(board_after):
            return 'allows_tactic'

        # Check for positional blunder
        if self._is_positional_blunder(board_before, move):
            return 'positional_blunder'

        return 'unspecified'

    async def _get_top_moves(
        self,
        board: chess.Board,
        engine: StockfishManager,
        n: int = 3
    ) -> List[Dict]:
        """Get top N moves with evaluations"""
        analysis = await engine.analyze_position(board)
        moves = []

        for i in range(min(n, len(analysis.multipv))):
            pv_info = analysis.multipv[i]
            moves.append({
                'move': pv_info['pv'][0].uci() if pv_info.get('pv') else None,
                'score': pv_info['score'],
                'depth': pv_info.get('depth', 0)
            })

        return moves
```

### 5. Main Pattern Analysis Orchestrator

```python
class PatternAnalysisEngine:
    """Main engine orchestrating all pattern detection"""

    def __init__(self, engine_config: EngineConfig):
        self.engine_config = engine_config
        self.tactical_detector = TacticalPatternDetector()
        self.opening_analyzer = OpeningAnalyzer()
        self.blunder_detector = BlunderDetector()

    async def analyze_game(
        self,
        pgn_text: str,
        username: str
    ) -> GameAnalysis:
        """Analyze complete game for patterns"""

        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if not game:
            raise ValueError("Invalid PGN")

        async with StockfishManager(self.engine_config) as engine:
            # Analyze opening
            opening_analysis = await self.opening_analyzer.analyze_opening(game, engine)

            # Analyze each move
            moves_analysis = []
            patterns_detected = set()
            critical_moments = []

            board = game.board()
            node = game
            move_num = 0

            while node.variations:
                move = node.variations[0].move
                move_num += 1

                # Analyze move
                move_analysis = await self.blunder_detector.analyze_move(
                    board,
                    move,
                    engine
                )

                # Detect tactical patterns
                board.push(move)
                tactical_patterns = await self.tactical_detector.detect(
                    board,
                    move,
                    move_analysis['eval_after']
                )

                if tactical_patterns:
                    for pattern in tactical_patterns:
                        patterns_detected.add(pattern['type'])

                # Mark critical moments
                if move_analysis['classification'] in ['blunder', 'critical_blunder']:
                    critical_moments.append(move_num)

                moves_analysis.append(move_analysis)
                node = node.variations[0]

            # Calculate accuracies
            white_accuracy = self._calculate_accuracy(moves_analysis, 'white')
            black_accuracy = self._calculate_accuracy(moves_analysis, 'black')

            return GameAnalysis(
                game_id=self._generate_game_id(pgn_text),
                analyzed_at=datetime.now(),
                white_accuracy=white_accuracy,
                black_accuracy=black_accuracy,
                opening_phase=opening_analysis,
                moves=moves_analysis,
                critical_moments=critical_moments,
                patterns_detected=list(patterns_detected)
            )

    def _calculate_accuracy(
        self,
        moves: List[Dict],
        color: str
    ) -> float:
        """Calculate accuracy percentage for a player"""
        color_moves = [
            m for i, m in enumerate(moves)
            if (color == 'white' and i % 2 == 0) or
               (color == 'black' and i % 2 == 1)
        ]

        if not color_moves:
            return 0.0

        good_moves = sum(
            1 for m in color_moves
            if m['classification'] in ['good', 'best']
        )

        return (good_moves / len(color_moves)) * 100

    async def analyze_multiple_games(
        self,
        games: List[Game],
        username: str,
        progress_callback: Optional[callable] = None
    ) -> List[GameAnalysis]:
        """Batch analyze multiple games"""
        analyses = []

        for i, game in enumerate(games):
            if progress_callback:
                await progress_callback(i, len(games))

            try:
                analysis = await self.analyze_game(game.pgn, username)
                analyses.append(analysis)
            except Exception as e:
                # Log error and continue
                print(f"Failed to analyze game {game.id}: {e}")
                continue

        return analyses
```

## Implementation Steps

1. Set up Stockfish engine manager
2. Implement tactical pattern detectors
3. Build opening analyzer with ECO database
4. Create blunder detection system
5. Develop move classification logic
6. Build main analysis orchestrator
7. Add batch processing capability
8. Implement progress tracking
9. Add comprehensive error handling
10. Optimize for performance

## Testing Requirements

### Unit Tests
- Test pattern detection accuracy
- Test move classification thresholds
- Test opening identification
- Test evaluation calculations
- Test error handling

### Integration Tests
- Test with sample PGN games
- Test Stockfish integration
- Test batch processing
- Test memory usage with 100 games
- Performance benchmarks

### Pattern Detection Tests
- Validate 90%+ blunder detection rate
- Test tactical pattern recognition
- Verify opening mistake detection
- Test edge cases (unusual positions)

## Acceptance Criteria

- [ ] Detects blunders with 90%+ accuracy
- [ ] Identifies common tactical patterns
- [ ] Analyzes opening phase correctly
- [ ] Processes game in < 2 seconds average
- [ ] Batch processes 100 games successfully
- [ ] Provides position evaluations
- [ ] Handles PGN parsing errors gracefully
- [ ] 85% test coverage
- [ ] Documentation complete

## Performance Optimization

```python
# Caching for repeated positions
position_cache = {}

# Connection pooling for Stockfish
engine_pool = []

# Batch evaluation of positions
async def batch_evaluate(positions: List[chess.Board]) -> List[float]:
    # Process positions in parallel
    pass
```

## Notes

- Stockfish must be installed in Docker container
- Consider using opening book for faster opening analysis
- Memory management important for batch processing
- Consider implementing analysis queuing for large batches
- Future: Add neural network for pattern recognition