"""
Ryx AI - Benchmarks Package

Provides:
- BaseBenchmark: Base class for creating benchmarks
- BenchmarkRunner: Runs benchmarks and collects results
- BenchmarkRegistry: Registry of all benchmarks

Usage:
    from core.benchmarks import BenchmarkRunner, BenchmarkRegistry
    
    # List available benchmarks
    print(BenchmarkRegistry.list_all())
    
    # Run a benchmark
    runner = BenchmarkRunner(executor=my_executor)
    result = await runner.run("coding_tasks")
    print(result.summary())
"""

from .base import (
    BaseBenchmark,
    Problem,
    ProblemResult,
    BenchmarkRun,
    BenchmarkCategory,
    BenchmarkRegistry,
    register_benchmark,
)

from .runner import (
    BenchmarkRunner,
    RunConfig,
    run_benchmark,
)

# Import benchmark implementations to register them
from . import coding_tasks
from . import bug_fixing

__all__ = [
    # Base classes
    'BaseBenchmark',
    'Problem',
    'ProblemResult',
    'BenchmarkRun',
    'BenchmarkCategory',
    'BenchmarkRegistry',
    'register_benchmark',
    
    # Runner
    'BenchmarkRunner',
    'RunConfig',
    'run_benchmark',
]
