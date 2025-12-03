"""
Ryx AI - RSI Package

Recursive Self-Improvement system.

The RSI Loop enables Ryx to autonomously improve itself:
1. Benchmark current capabilities
2. Analyze weaknesses
3. Generate improvement hypotheses
4. Implement in sandbox
5. Test improvements
6. Accept or reject based on benchmarks

Usage:
    from core.rsi import RSILoop, RSIConfig
    
    config = RSIConfig(
        benchmarks=["coding_tasks", "bug_fixing"],
        min_improvement=0.01,
        require_approval=True
    )
    
    rsi = RSILoop(config)
    await rsi.initialize(llm_client=my_llm)
    
    # Run one iteration
    result = await rsi.iterate()
    
    # Or run continuously
    await rsi.run_loop(max_iterations=10)
"""

from .loop import (
    RSILoop,
    RSIConfig,
    RSIPhase,
    RSIIteration,
    ImprovementHypothesis,
)

__all__ = [
    'RSILoop',
    'RSIConfig',
    'RSIPhase',
    'RSIIteration',
    'ImprovementHypothesis',
]
