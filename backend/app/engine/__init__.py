"""Chess analysis engine package."""

from .stockfish_manager import StockfishManager, test_stockfish_installation
from .pattern_detector import TacticalPatternDetector
from .opening_analyzer import OpeningAnalyzer
from .blunder_detector import BlunderDetector
from .analysis_engine import PatternAnalysisEngine

__all__ = [
    "StockfishManager",
    "test_stockfish_installation",
    "TacticalPatternDetector",
    "OpeningAnalyzer",
    "BlunderDetector",
    "PatternAnalysisEngine",
]
