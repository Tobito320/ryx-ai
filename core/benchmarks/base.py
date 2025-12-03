"""
Ryx AI - Benchmark System

Core benchmark infrastructure for measuring Ryx capabilities.
Used by the RSI loop to:
1. Measure current performance (baseline)
2. Compare before/after self-improvement
3. Decide whether to accept/reject changes

Inspired by: self_improving_coding_agent/base_agent/src/benchmarks/
"""

import json
import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, List, Dict, Optional, ClassVar
from enum import Enum

logger = logging.getLogger(__name__)


class BenchmarkCategory(Enum):
    """Categories of benchmarks"""
    CODING = "coding"           # Code generation tasks
    FIXING = "fixing"           # Bug fixing tasks
    PLANNING = "planning"       # Multi-step planning
    TOOL_USE = "tool_use"       # Tool calling accuracy
    REASONING = "reasoning"     # Complex reasoning
    SELF_HEALING = "self_healing"  # Error recovery


@dataclass
class Problem:
    """A single benchmark problem"""
    problem_id: str
    category: BenchmarkCategory
    statement: str              # The task/problem description
    expected_output: Any        # Expected result (can be code, answer, etc.)
    validation_type: str = "exact"  # exact, contains, regex, function
    difficulty: int = 1         # 1-5 scale
    timeout_seconds: int = 60
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['category'] = self.category.value
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'Problem':
        d['category'] = BenchmarkCategory(d['category'])
        return cls(**d)


@dataclass
class ProblemResult:
    """Result of running a single problem"""
    problem_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Outcome
    score: Optional[float] = None       # 0.0 to 1.0
    passed: bool = False
    
    # Metrics
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    wall_time_seconds: float = 0.0
    
    # Status
    timed_out: bool = False
    error: Optional[str] = None
    
    # Output
    actual_output: Optional[str] = None
    
    def is_complete(self) -> bool:
        return self.score is not None or self.error is not None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BenchmarkRun:
    """A complete benchmark run (multiple problems)"""
    run_id: str
    benchmark_name: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    
    # Results
    results: Dict[str, ProblemResult] = field(default_factory=dict)
    
    # Aggregate metrics
    total_problems: int = 0
    passed_count: int = 0
    failed_count: int = 0
    timed_out_count: int = 0
    error_count: int = 0
    
    # Performance
    average_score: float = 0.0
    total_tokens: int = 0
    total_time_seconds: float = 0.0
    
    def add_result(self, result: ProblemResult):
        """Add a problem result and update aggregates"""
        self.results[result.problem_id] = result
        self.total_problems = len(self.results)
        
        if result.passed:
            self.passed_count += 1
        elif result.timed_out:
            self.timed_out_count += 1
        elif result.error:
            self.error_count += 1
        else:
            self.failed_count += 1
        
        self.total_tokens += result.tokens_used
        self.total_time_seconds += result.wall_time_seconds
        
        # Recalculate average score
        scores = [r.score for r in self.results.values() if r.score is not None]
        self.average_score = sum(scores) / len(scores) if scores else 0.0
    
    def finalize(self):
        """Mark run as complete"""
        self.finished_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['results'] = {k: v.to_dict() if hasattr(v, 'to_dict') else v 
                        for k, v in self.results.items()}
        return d
    
    def summary(self) -> str:
        """Human-readable summary"""
        return f"""Benchmark: {self.benchmark_name}
Run ID: {self.run_id}
─────────────────────────────
Total: {self.total_problems} problems
Passed: {self.passed_count} ({self.passed_count/self.total_problems*100:.1f}%)
Failed: {self.failed_count}
Timed out: {self.timed_out_count}
Errors: {self.error_count}

Average Score: {self.average_score:.2f}
Total Tokens: {self.total_tokens:,}
Total Time: {self.total_time_seconds:.1f}s
"""


class BaseBenchmark(ABC):
    """
    Base class for all benchmarks.
    
    Subclasses must implement:
    - problems: List of Problem instances
    - score_problem: How to evaluate a response
    """
    
    name: ClassVar[str] = "base"
    description: ClassVar[str] = ""
    category: ClassVar[BenchmarkCategory] = BenchmarkCategory.CODING
    
    def __init__(self):
        self._problems: Optional[List[Problem]] = None
    
    @property
    @abstractmethod
    def problems(self) -> List[Problem]:
        """Return list of problems for this benchmark"""
        pass
    
    @abstractmethod
    async def score_problem(
        self,
        problem: Problem,
        response: str,
        context: Optional[Dict] = None
    ) -> tuple[float, bool, Optional[str]]:
        """
        Score a response to a problem.
        
        Args:
            problem: The problem that was attempted
            response: The model's response
            context: Optional context (working dir, files created, etc.)
            
        Returns:
            (score, passed, error_message)
            - score: 0.0 to 1.0
            - passed: True if problem was solved
            - error_message: If there was an error
        """
        pass
    
    def get_problem(self, problem_id: str) -> Optional[Problem]:
        """Get a specific problem by ID"""
        for p in self.problems:
            if p.problem_id == problem_id:
                return p
        return None
    
    async def setup_problem(self, problem: Problem, work_dir: Path) -> None:
        """Optional: Setup before running a problem (create files, etc.)"""
        pass
    
    async def cleanup_problem(self, problem: Problem, work_dir: Path) -> None:
        """Optional: Cleanup after running a problem"""
        pass


class BenchmarkRegistry:
    """Registry of all available benchmarks"""
    
    _benchmarks: Dict[str, type] = {}
    
    @classmethod
    def register(cls, benchmark_class: type):
        """Register a benchmark class"""
        name = getattr(benchmark_class, 'name', benchmark_class.__name__)
        cls._benchmarks[name] = benchmark_class
        return benchmark_class
    
    @classmethod
    def get(cls, name: str) -> Optional[type]:
        """Get a benchmark class by name"""
        return cls._benchmarks.get(name)
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered benchmarks"""
        return list(cls._benchmarks.keys())
    
    @classmethod
    def create(cls, name: str) -> Optional[BaseBenchmark]:
        """Create a benchmark instance by name"""
        benchmark_class = cls.get(name)
        if benchmark_class:
            return benchmark_class()
        return None


def register_benchmark(cls):
    """Decorator to register a benchmark"""
    BenchmarkRegistry.register(cls)
    return cls
