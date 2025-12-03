"""
Ryx AI - Benchmark Runner

Executes benchmarks and manages results.
Can run:
- Single benchmark
- All benchmarks
- Specific problem
- Comparison between runs
"""

import os
import json
import asyncio
import tempfile
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, asdict
import uuid

from .base import (
    BaseBenchmark, Problem, ProblemResult, BenchmarkRun,
    BenchmarkRegistry, BenchmarkCategory
)

logger = logging.getLogger(__name__)


@dataclass
class RunConfig:
    """Configuration for a benchmark run"""
    max_concurrent: int = 1         # Parallel problems (1 = sequential)
    timeout_seconds: int = 120      # Per-problem timeout
    save_results: bool = True       # Save to disk
    results_dir: Optional[Path] = None
    verbose: bool = False
    
    # Model config (passed to executor)
    model: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096


class BenchmarkRunner:
    """
    Runs benchmarks and collects results.
    
    Usage:
        runner = BenchmarkRunner()
        
        # Run a single benchmark
        result = await runner.run("coding_tasks")
        
        # Run all benchmarks
        results = await runner.run_all()
        
        # Compare two runs
        diff = runner.compare(run_id_1, run_id_2)
    """
    
    def __init__(
        self,
        executor: Optional[Callable] = None,
        results_dir: Optional[Path] = None
    ):
        """
        Args:
            executor: Async function that runs a problem and returns response
                     Signature: async (problem: Problem, config: RunConfig) -> str
            results_dir: Where to save benchmark results
        """
        self.executor = executor
        
        if results_dir:
            self.results_dir = Path(results_dir)
        else:
            # Default: ~/ryx-ai/data/benchmarks/
            self.results_dir = Path.home() / "ryx-ai" / "data" / "benchmarks"
        
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def set_executor(self, executor: Callable):
        """Set the executor function"""
        self.executor = executor
    
    async def run(
        self,
        benchmark_name: str,
        config: Optional[RunConfig] = None,
        problem_ids: Optional[List[str]] = None
    ) -> BenchmarkRun:
        """
        Run a benchmark.
        
        Args:
            benchmark_name: Name of the benchmark to run
            config: Run configuration
            problem_ids: Specific problems to run (None = all)
            
        Returns:
            BenchmarkRun with all results
        """
        config = config or RunConfig()
        
        # Get benchmark
        benchmark = BenchmarkRegistry.create(benchmark_name)
        if not benchmark:
            raise ValueError(f"Unknown benchmark: {benchmark_name}. Available: {BenchmarkRegistry.list_all()}")
        
        # Get problems
        problems = benchmark.problems
        if problem_ids:
            problems = [p for p in problems if p.problem_id in problem_ids]
        
        if not problems:
            raise ValueError(f"No problems found for benchmark: {benchmark_name}")
        
        # Create run
        run_id = f"{benchmark_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        run = BenchmarkRun(
            run_id=run_id,
            benchmark_name=benchmark_name,
            total_problems=len(problems)
        )
        
        logger.info(f"Starting benchmark: {benchmark_name} ({len(problems)} problems)")
        
        # Create temp work directory
        with tempfile.TemporaryDirectory(prefix="ryx_bench_") as work_dir:
            work_path = Path(work_dir)
            
            if config.max_concurrent > 1:
                # Parallel execution
                semaphore = asyncio.Semaphore(config.max_concurrent)
                
                async def run_with_semaphore(problem):
                    async with semaphore:
                        return await self._run_problem(
                            benchmark, problem, work_path, config
                        )
                
                results = await asyncio.gather(
                    *[run_with_semaphore(p) for p in problems],
                    return_exceptions=True
                )
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Problem failed with exception: {result}")
                    else:
                        run.add_result(result)
            else:
                # Sequential execution
                for i, problem in enumerate(problems, 1):
                    if config.verbose:
                        logger.info(f"[{i}/{len(problems)}] Running: {problem.problem_id}")
                    
                    result = await self._run_problem(
                        benchmark, problem, work_path, config
                    )
                    run.add_result(result)
                    
                    if config.verbose:
                        status = "✓" if result.passed else "✗"
                        logger.info(f"  {status} Score: {result.score:.2f}")
        
        # Finalize
        run.finalize()
        
        # Save results
        if config.save_results:
            self._save_run(run)
        
        logger.info(f"Benchmark complete: {run.passed_count}/{run.total_problems} passed")
        
        return run
    
    async def _run_problem(
        self,
        benchmark: BaseBenchmark,
        problem: Problem,
        work_dir: Path,
        config: RunConfig
    ) -> ProblemResult:
        """Run a single problem"""
        result = ProblemResult(problem_id=problem.problem_id)
        
        start_time = datetime.now()
        
        try:
            # Setup
            await benchmark.setup_problem(problem, work_dir)
            
            # Execute with timeout
            timeout = min(problem.timeout_seconds, config.timeout_seconds)
            
            if self.executor:
                try:
                    response = await asyncio.wait_for(
                        self.executor(problem, config),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    result.timed_out = True
                    result.score = 0.0
                    return result
            else:
                # No executor - just return empty (for testing)
                response = ""
            
            # Score
            score, passed, error = await benchmark.score_problem(
                problem, response, {"work_dir": str(work_dir)}
            )
            
            result.score = score
            result.passed = passed
            result.actual_output = response[:1000] if response else None
            if error:
                result.error = error
            
            # Cleanup
            await benchmark.cleanup_problem(problem, work_dir)
            
        except Exception as e:
            result.error = str(e)
            result.score = 0.0
            logger.error(f"Error running problem {problem.problem_id}: {e}")
        
        finally:
            result.wall_time_seconds = (datetime.now() - start_time).total_seconds()
        
        return result
    
    async def run_all(self, config: Optional[RunConfig] = None) -> Dict[str, BenchmarkRun]:
        """Run all registered benchmarks"""
        config = config or RunConfig()
        results = {}
        
        for name in BenchmarkRegistry.list_all():
            try:
                results[name] = await self.run(name, config)
            except Exception as e:
                logger.error(f"Failed to run benchmark {name}: {e}")
        
        return results
    
    def _save_run(self, run: BenchmarkRun):
        """Save a run to disk"""
        run_file = self.results_dir / f"{run.run_id}.json"
        with open(run_file, 'w') as f:
            json.dump(run.to_dict(), f, indent=2)
        logger.debug(f"Saved benchmark run to: {run_file}")
    
    def load_run(self, run_id: str) -> Optional[BenchmarkRun]:
        """Load a run from disk"""
        run_file = self.results_dir / f"{run_id}.json"
        if not run_file.exists():
            return None
        
        with open(run_file) as f:
            data = json.load(f)
        
        run = BenchmarkRun(
            run_id=data['run_id'],
            benchmark_name=data['benchmark_name'],
            started_at=data['started_at'],
            finished_at=data.get('finished_at')
        )
        
        # Restore results
        for pid, result_data in data.get('results', {}).items():
            run.results[pid] = ProblemResult(**result_data)
        
        # Restore aggregates
        run.total_problems = data.get('total_problems', 0)
        run.passed_count = data.get('passed_count', 0)
        run.failed_count = data.get('failed_count', 0)
        run.timed_out_count = data.get('timed_out_count', 0)
        run.error_count = data.get('error_count', 0)
        run.average_score = data.get('average_score', 0.0)
        run.total_tokens = data.get('total_tokens', 0)
        run.total_time_seconds = data.get('total_time_seconds', 0.0)
        
        return run
    
    def list_runs(self, benchmark_name: Optional[str] = None) -> List[str]:
        """List all saved runs"""
        runs = []
        for f in self.results_dir.glob("*.json"):
            run_id = f.stem
            if benchmark_name is None or run_id.startswith(benchmark_name):
                runs.append(run_id)
        return sorted(runs, reverse=True)  # Newest first
    
    def get_baseline(self, benchmark_name: str) -> Optional[BenchmarkRun]:
        """Get the baseline run for a benchmark"""
        baseline_file = self.results_dir / f"{benchmark_name}_baseline.json"
        if baseline_file.exists():
            with open(baseline_file) as f:
                data = json.load(f)
            return self.load_run(data.get('run_id'))
        return None
    
    def set_baseline(self, run_id: str):
        """Set a run as the baseline for its benchmark"""
        run = self.load_run(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")
        
        baseline_file = self.results_dir / f"{run.benchmark_name}_baseline.json"
        with open(baseline_file, 'w') as f:
            json.dump({
                'run_id': run_id,
                'set_at': datetime.now().isoformat(),
                'average_score': run.average_score,
                'passed_count': run.passed_count,
                'total_problems': run.total_problems
            }, f, indent=2)
        
        logger.info(f"Set baseline for {run.benchmark_name}: {run_id}")
    
    def compare(self, run_id_1: str, run_id_2: str) -> Dict[str, Any]:
        """
        Compare two benchmark runs.
        
        Returns dict with:
        - improved: List of problem_ids that got better
        - regressed: List of problem_ids that got worse
        - unchanged: List of problem_ids with same result
        - score_diff: Difference in average score
        """
        run1 = self.load_run(run_id_1)
        run2 = self.load_run(run_id_2)
        
        if not run1 or not run2:
            raise ValueError(f"Could not load runs: {run_id_1}, {run_id_2}")
        
        improved = []
        regressed = []
        unchanged = []
        
        # Compare problem by problem
        all_problems = set(run1.results.keys()) | set(run2.results.keys())
        
        for pid in all_problems:
            r1 = run1.results.get(pid)
            r2 = run2.results.get(pid)
            
            if not r1 or not r2:
                continue
            
            score1 = r1.score or 0.0
            score2 = r2.score or 0.0
            
            if score2 > score1 + 0.01:
                improved.append(pid)
            elif score2 < score1 - 0.01:
                regressed.append(pid)
            else:
                unchanged.append(pid)
        
        return {
            'run1': run_id_1,
            'run2': run_id_2,
            'improved': improved,
            'regressed': regressed,
            'unchanged': unchanged,
            'improved_count': len(improved),
            'regressed_count': len(regressed),
            'score_diff': run2.average_score - run1.average_score,
            'run1_score': run1.average_score,
            'run2_score': run2.average_score,
            'is_improvement': len(regressed) == 0 and run2.average_score >= run1.average_score
        }


# Convenience function for quick benchmarking
async def run_benchmark(
    benchmark_name: str,
    executor: Callable,
    **kwargs
) -> BenchmarkRun:
    """Quick way to run a benchmark"""
    runner = BenchmarkRunner(executor=executor)
    config = RunConfig(**kwargs)
    return await runner.run(benchmark_name, config)
