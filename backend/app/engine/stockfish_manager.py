"""
Stockfish engine manager.

Handles Stockfish lifecycle, configuration, and position evaluation.
"""

import asyncio
import chess
import chess.engine
from typing import Optional, Dict, List
from pathlib import Path

from app.models.chess_models import EngineConfig, PositionEvaluation


class StockfishManager:
    """
    Manage Stockfish chess engine with async context manager support.

    Provides position evaluation, move suggestions, and multi-PV analysis.
    Optimized for batch processing with connection reuse.
    """

    def __init__(self, config: EngineConfig):
        """
        Initialize Stockfish manager.

        Args:
            config: Engine configuration settings
        """
        self.config = config
        self.engine: Optional[chess.engine.SimpleEngine] = None
        self._position_cache: Dict[str, PositionEvaluation] = {}

    async def __aenter__(self) -> "StockfishManager":
        """Start engine as async context manager."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop engine when exiting context."""
        await self.stop()

    async def start(self) -> None:
        """
        Start the Stockfish engine.

        Raises:
            FileNotFoundError: If Stockfish binary not found
            RuntimeError: If engine fails to start
        """
        engine_path = Path(self.config.path)

        if not engine_path.exists():
            raise FileNotFoundError(
                f"Stockfish not found at {self.config.path}. "
                "Please install Stockfish or update STOCKFISH_PATH in config."
            )

        try:
            # Start UCI engine
            self.engine = await chess.engine.popen_uci(str(engine_path))

            # Configure engine options
            await self.engine.configure({
                "Threads": self.config.threads,
                "Hash": self.config.hash_size,
                "MultiPV": self.config.multipv,
            })

        except Exception as e:
            raise RuntimeError(f"Failed to start Stockfish engine: {e}")

    async def stop(self) -> None:
        """Stop the Stockfish engine gracefully."""
        if self.engine:
            try:
                await self.engine.quit()
            except Exception:
                pass  # Engine already stopped
            finally:
                self.engine = None

        # Clear cache
        self._position_cache.clear()

    async def analyze_position(
        self,
        board: chess.Board,
        depth: Optional[int] = None,
        time_limit: Optional[float] = None,
        multipv: Optional[int] = None,
        use_cache: bool = True,
    ) -> Dict:
        """
        Analyze a chess position.

        Args:
            board: Chess board position
            depth: Search depth (overrides config default)
            time_limit: Time limit in seconds (overrides config default)
            multipv: Number of principal variations (overrides config default)
            use_cache: Whether to use cached results for repeated positions

        Returns:
            Dictionary with analysis results including score, best move, and PV

        Raises:
            RuntimeError: If engine not started
        """
        if not self.engine:
            raise RuntimeError("Engine not started. Use 'async with' or call start() first.")

        # Check cache
        cache_key = board.fen()
        if use_cache and cache_key in self._position_cache:
            cached = self._position_cache[cache_key]
            return {
                "score": cached.centipawns,
                "mate": cached.mate_in,
                "best_move": cached.best_move,
                "depth": cached.depth,
                "cached": True,
            }

        # Set up analysis parameters
        analysis_depth = depth or self.config.depth
        analysis_time = time_limit or self.config.time_limit
        analysis_multipv = multipv or self.config.multipv

        # Configure MultiPV if different from current setting
        if analysis_multipv != self.config.multipv:
            await self.engine.configure({"MultiPV": analysis_multipv})

        # Analyze position
        limit = chess.engine.Limit(
            depth=analysis_depth,
            time=analysis_time
        )

        info = await self.engine.analyse(board, limit, multipv=analysis_multipv)

        # Extract score
        score = info.get("score")
        if not score:
            return {
                "score": None,
                "mate": None,
                "best_move": None,
                "depth": analysis_depth,
                "cached": False,
            }

        # Get relative score for side to move
        relative_score = score.relative

        # Extract evaluation
        if relative_score.is_mate():
            mate_in = relative_score.mate()
            centipawns = None
        else:
            mate_in = None
            centipawns = relative_score.score()

        # Get best move from principal variation
        pv = info.get("pv", [])
        best_move = pv[0].uci() if pv else None

        result = {
            "score": centipawns,
            "mate": mate_in,
            "best_move": best_move,
            "depth": info.get("depth", analysis_depth),
            "pv": [move.uci() for move in pv[:5]],  # First 5 moves of PV
            "multipv": info.get("multipv", []),
            "cached": False,
        }

        # Cache the result
        if use_cache:
            self._position_cache[cache_key] = PositionEvaluation(
                centipawns=centipawns,
                mate_in=mate_in,
                depth=info.get("depth", analysis_depth),
                best_move=best_move,
            )

        return result

    async def get_top_moves(
        self,
        board: chess.Board,
        num_moves: int = 3,
        depth: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get top N moves for a position.

        Args:
            board: Chess board position
            num_moves: Number of top moves to return (1-5)
            depth: Search depth

        Returns:
            List of dictionaries with move, score, and evaluation
        """
        if not self.engine:
            raise RuntimeError("Engine not started")

        num_moves = max(1, min(num_moves, 5))  # Clamp to 1-5

        # Configure MultiPV
        await self.engine.configure({"MultiPV": num_moves})

        # Analyze
        analysis_depth = depth or self.config.depth
        limit = chess.engine.Limit(depth=analysis_depth)

        info = await self.engine.analyse(board, limit, multipv=num_moves)

        # Extract all PV lines
        top_moves = []

        # Handle single PV (MultiPV = 1)
        if "pv" in info:
            pv = info["pv"]
            score = info["score"].relative
            if pv:
                top_moves.append({
                    "move": pv[0].uci(),
                    "score": score.score() if not score.is_mate() else None,
                    "mate": score.mate() if score.is_mate() else None,
                    "pv": [m.uci() for m in pv[:5]],
                })

        # Handle multiple PVs
        if "multipv" in info:
            top_moves = []
            for pv_info in info["multipv"]:
                pv = pv_info.get("pv", [])
                score = pv_info["score"].relative
                if pv:
                    top_moves.append({
                        "move": pv[0].uci(),
                        "score": score.score() if not score.is_mate() else None,
                        "mate": score.mate() if score.is_mate() else None,
                        "pv": [m.uci() for m in pv[:5]],
                    })

        return top_moves[:num_moves]

    async def evaluate_move(
        self,
        board_before: chess.Board,
        move: chess.Move,
        depth: Optional[int] = None,
    ) -> Dict:
        """
        Evaluate a specific move.

        Args:
            board_before: Position before the move
            move: The move to evaluate
            depth: Search depth

        Returns:
            Dictionary with evaluation before and after the move
        """
        # Evaluate position before move
        eval_before = await self.analyze_position(board_before, depth=depth)

        # Make the move
        board_after = board_before.copy()
        board_after.push(move)

        # Evaluate position after move
        eval_after = await self.analyze_position(board_after, depth=depth)

        # Get best move in original position
        top_moves = await self.get_top_moves(board_before, num_moves=1, depth=depth)
        best_move = top_moves[0] if top_moves else None

        return {
            "move": move.uci(),
            "eval_before": eval_before["score"],
            "eval_after": eval_after["score"],
            "mate_before": eval_before["mate"],
            "mate_after": eval_after["mate"],
            "best_move": best_move["move"] if best_move else None,
            "best_eval": best_move["score"] if best_move else None,
        }

    def clear_cache(self) -> None:
        """Clear the position evaluation cache."""
        self._position_cache.clear()

    def get_cache_size(self) -> int:
        """Get number of cached positions."""
        return len(self._position_cache)


async def test_stockfish_installation(stockfish_path: str = "/usr/local/bin/stockfish") -> bool:
    """
    Test if Stockfish is properly installed and working.

    Args:
        stockfish_path: Path to Stockfish binary

    Returns:
        True if Stockfish is working, False otherwise
    """
    try:
        config = EngineConfig(path=stockfish_path, depth=10)
        async with StockfishManager(config) as manager:
            # Test with starting position
            board = chess.Board()
            result = await manager.analyze_position(board, depth=10)
            return result["best_move"] is not None
    except Exception as e:
        print(f"Stockfish test failed: {e}")
        return False
