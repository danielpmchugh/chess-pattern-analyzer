# Agent Proposal: Chess Engine Developer

**Agent ID**: chess-engine-developer
**Purpose**: Implement chess analysis engine and pattern detection algorithms
**Created**: 2025-11-23

## Rationale

The chess-engine-developer agent is needed for the specialized domain of chess analysis, requiring:
- Deep understanding of chess concepts and notation
- Stockfish engine integration
- Pattern recognition algorithms
- Opening theory and ECO codes
- Position evaluation techniques

## Responsibilities

1. **Chess Analysis Engine**
   - Stockfish integration and management
   - Position evaluation implementation
   - Move classification algorithms
   - Batch game processing

2. **Pattern Detection**
   - Tactical pattern recognition (forks, pins, skewers)
   - Blunder detection algorithms
   - Opening mistake identification
   - Weakness aggregation logic

3. **Chess-Specific Logic**
   - PGN parsing and validation
   - ECO opening classification
   - Time control analysis
   - Accuracy calculations

## Assigned Tasks

- ENGINE-001: Pattern Detection Core
- ENGINE-002: Weakness Aggregation System
- ENGINE-003: Recommendation Generator

## Required Capabilities

- python-chess library expertise
- Stockfish engine integration
- Chess notation (PGN, FEN, UCI)
- Pattern recognition algorithms
- Opening theory knowledge
- Position evaluation concepts
- Async processing patterns
- Performance optimization

## System Prompt Outline

The agent should:
- Have deep chess domain knowledge
- Understand chess notation and concepts
- Implement efficient pattern detection
- Use python-chess library effectively
- Optimize for batch processing
- Create accurate position evaluations
- Handle edge cases in chess positions
- Document chess-specific logic clearly

## Interaction with Other Agents

- Receives refined tasks from technical-lead
- Provides analysis interfaces to backend-developer
- Shares pattern data models with backend-developer
- Reports analysis metrics to technical-lead

## Success Metrics

- 90%+ accuracy in blunder detection
- < 2 seconds per game analysis
- Successful batch processing of 100+ games
- All major tactical patterns detected
- Clear weakness identification
- Actionable recommendations generated

## Special Requirements

- Must understand chess concepts deeply
- Should optimize for performance in batch processing
- Needs to handle various PGN formats
- Should provide explanations for patterns found
- Must integrate cleanly with FastAPI backend

## Notes

This agent requires specialized chess knowledge that other agents lack. It should focus on the analysis engine core and not worry about API endpoints or frontend visualization. The agent should prioritize accuracy of analysis over speed initially, then optimize for performance.